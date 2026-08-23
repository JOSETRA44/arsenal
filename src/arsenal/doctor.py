"""Audit each registered CLI against ARSENAL-SPEC.md.

The point of this module is that spec conformance is *checked*, not asserted in
a README. Adding a tool to the arsenal, or changing one, gets graded the same
way every time.

Checks come in two tiers:

``static``
    Nothing but ``--help`` and ``describe --json`` — no network, no API keys,
    safe to run in CI on every commit.
``live``
    Actually executes one declared example per tool and inspects the envelope
    it produced. This is the only way to verify the envelope, the cache flag
    and the exit codes are real rather than documented, but it costs network
    calls and API quota, so it is opt-in.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from typing import Any, Literal

from .registry import Tool
from .runner import EXIT_MEANINGS, Invocation, ToolUnavailable, invoke

Status = Literal["pass", "fail", "warn", "skip"]

REQUIRED_FORMATS = ("table", "json", "jsonl", "csv", "md")
REQUIRED_MANIFEST_KEYS = ("name", "version", "source", "formats", "exit_codes", "commands")
REQUIRED_COMMAND_KEYS = ("name", "summary")
REQUIRED_ENVELOPE_KEYS = ("ok", "command", "source", "fetched_at", "cached", "count", "data", "rows")


@dataclass
class Finding:
    """One graded observation about one tool."""

    check: str
    status: Status
    detail: str
    hint: str = ""

    @property
    def ok(self) -> bool:
        return self.status in ("pass", "skip")


@dataclass
class Report:
    """Every finding for one tool, plus the manifest if we managed to read one."""

    tool: str
    findings: list[Finding] = field(default_factory=list)
    manifest: dict[str, Any] | None = None

    def add(self, check: str, status: Status, detail: str, hint: str = "") -> Finding:
        finding = Finding(check=check, status=status, detail=detail, hint=hint)
        self.findings.append(finding)
        return finding

    @property
    def failed(self) -> list[Finding]:
        return [f for f in self.findings if f.status == "fail"]

    @property
    def warned(self) -> list[Finding]:
        return [f for f in self.findings if f.status == "warn"]

    @property
    def score(self) -> tuple[int, int]:
        """(passed, graded) — ``skip`` findings are excluded from the denominator."""
        graded = [f for f in self.findings if f.status != "skip"]
        return sum(1 for f in graded if f.status == "pass"), len(graded)

    @property
    def compliant(self) -> bool:
        return not self.failed

    def to_dict(self) -> dict[str, Any]:
        passed, graded = self.score
        return {
            "tool": self.tool,
            "compliant": self.compliant,
            "passed": passed,
            "graded": graded,
            "findings": [
                {"check": f.check, "status": f.status, "detail": f.detail, "hint": f.hint}
                for f in self.findings
            ],
        }


def audit(
    tool: Tool, *, live: bool = False, timeout: int = 120, prefer: str = "installed"
) -> Report:
    """Grade one tool against the spec.

    ``prefer="source"`` audits the working tree rather than an installed copy -
    the right choice while a change is still in flight.
    """
    report = Report(tool=tool.name)

    try:
        help_run = invoke(tool, ["--help"], timeout=timeout, prefer=prefer)
    except ToolUnavailable as exc:
        report.add("available", "fail", str(exc), hint=f"uv tool install {tool.path}")
        return report

    report.add("available", "pass", " ".join(help_run.argv[:-1]))
    _check_help(report, help_run)
    manifest = _check_describe(report, tool, timeout, prefer)
    if manifest is not None:
        report.manifest = manifest
        _check_manifest(report, manifest)

    if live:
        _check_live(report, tool, manifest, timeout, prefer)
    else:
        report.add("live", "skip", "live checks not requested", hint="re-run with --live")
    return report


def _check_help(report: Report, run: Invocation) -> None:
    if run.exit_code != 0:
        report.add(
            "help",
            "fail",
            "`--help` exited " + str(run.exit_code),
            hint="`--help` must exit 0 so a caller can probe a tool safely.",
        )
        return
    report.add("help", "pass", "`--help` exits 0")


def _check_describe(
    report: Report, tool: Tool, timeout: int, prefer: str = "installed"
) -> dict[str, Any] | None:
    run = invoke(tool, ["describe", "--json"], timeout=timeout, prefer=prefer)
    if run.exit_code != 0:
        detail = (run.stderr or run.stdout).strip()[:200]
        report.add(
            "describe",
            "fail",
            "`describe --json` exited " + str(run.exit_code) + ": " + detail,
            hint="Spec section 4: every tool must publish a machine-readable manifest.",
        )
        return None
    payload = run.json()
    if payload is None:
        report.add(
            "describe",
            "fail",
            "`describe --json` did not produce parseable JSON on stdout",
            hint="stdout must carry only the manifest; notes belong on stderr.",
        )
        return None
    # The manifest may be delivered bare or wrapped in the standard envelope.
    if isinstance(payload, dict) and "data" in payload and "ok" in payload:
        manifest = payload["data"]
    else:
        manifest = payload
    if not isinstance(manifest, dict):
        report.add("describe", "fail", "manifest is " + type(manifest).__name__ + ", expected object")
        return None
    report.add("describe", "pass", "`describe --json` returns a JSON object")
    return manifest


def _check_manifest(report: Report, manifest: dict[str, Any]) -> None:
    missing = [k for k in REQUIRED_MANIFEST_KEYS if k not in manifest]
    if missing:
        report.add(
            "manifest.keys",
            "fail",
            "missing manifest keys: " + ", ".join(missing),
            hint="Spec section 4 requires: " + ", ".join(REQUIRED_MANIFEST_KEYS),
        )
    else:
        report.add("manifest.keys", "pass", "all required manifest keys present")

    formats = manifest.get("formats") or []
    missing_formats = [f for f in REQUIRED_FORMATS if f not in formats]
    if missing_formats:
        report.add(
            "formats",
            "fail",
            "manifest omits format(s): " + ", ".join(missing_formats),
            hint="Spec section 1 requires all of: " + ", ".join(REQUIRED_FORMATS),
        )
    else:
        extra = [f for f in formats if f not in REQUIRED_FORMATS]
        note = " (plus " + ", ".join(extra) + ")" if extra else ""
        report.add("formats", "pass", "declares all five required formats" + note)

    exit_codes = manifest.get("exit_codes") or {}
    declared = {str(k) for k in exit_codes}
    missing_codes = [str(c) for c in EXIT_MEANINGS if str(c) not in declared]
    if missing_codes:
        # A tool with no network and no auth genuinely has no code 4/5/6 path;
        # that is a documentation gap, not a defect, so warn rather than fail.
        report.add(
            "exit_codes",
            "warn",
            "manifest does not document exit code(s): " + ", ".join(missing_codes),
            hint="Document inapplicable codes explicitly, e.g. 'n/a - no external API'.",
        )
    else:
        report.add("exit_codes", "pass", "all seven exit codes documented")

    commands = manifest.get("commands") or []
    if not commands:
        report.add("commands", "fail", "manifest lists no commands")
        return
    malformed = [
        (c.get("name", "<unnamed>") if isinstance(c, dict) else "<not-an-object>")
        for c in commands
        if not isinstance(c, dict) or any(k not in c for k in REQUIRED_COMMAND_KEYS)
    ]
    if malformed:
        report.add(
            "commands",
            "fail",
            str(len(malformed)) + " command(s) missing required keys: " + ", ".join(malformed[:5]),
            hint="Each command needs at least: " + ", ".join(REQUIRED_COMMAND_KEYS),
        )
    else:
        report.add("commands", "pass", str(len(commands)) + " commands, all well-formed")

    with_examples = [c for c in commands if isinstance(c, dict) and c.get("examples")]
    if not with_examples:
        report.add(
            "examples",
            "warn",
            "no command carries an example",
            hint="Examples are how an agent learns the tool without reading source.",
        )
    else:
        report.add(
            "examples",
            "pass",
            str(len(with_examples)) + "/" + str(len(commands)) + " commands carry examples",
        )


def _check_live(
    report: Report,
    tool: Tool,
    manifest: dict[str, Any] | None,
    timeout: int,
    prefer: str = "installed",
) -> None:
    """Run one declared example and inspect the envelope it produced."""
    if manifest is None:
        report.add("live", "skip", "no manifest to draw an example from")
        return
    example = _first_example(manifest)
    if example is None:
        report.add("live", "skip", "manifest declares no runnable example")
        return

    args = _example_args(example, tool.script)
    if args is None:
        report.add("live.envelope", "warn", "could not parse example: " + example)
        return

    run = invoke(tool, [*args, "--format", "json"], timeout=timeout, prefer=prefer)
    payload = run.json()
    if payload is None:
        detail = (run.stderr or run.stdout).strip()[:160]
        report.add(
            "live.envelope",
            "fail",
            "`" + " ".join(args) + " --format json` produced no parseable JSON"
            " (exit " + str(run.exit_code) + ": " + detail + ")",
            hint="Spec section 1: --format json must emit the envelope on stdout.",
        )
        return
    if not isinstance(payload, dict):
        report.add("live.envelope", "fail", "envelope is " + type(payload).__name__ + ", expected object")
        return

    if payload.get("ok") is False:
        # The upstream refused, but a well-formed error envelope is exactly
        # what the spec asks for in that case - the tool passed, the source
        # did not. Grading this as a tool defect would blame the wrong party.
        missing = [k for k in ("ok", "command", "source", "error") if k not in payload]
        error = payload.get("error") or {}
        if missing or not isinstance(error, dict) or "code" not in error:
            report.add(
                "live.envelope",
                "fail",
                "error envelope malformed: missing " + ", ".join(missing or ["error.code"]),
                hint="Spec section 1 requires ok/command/source/error{code,message,hint}.",
            )
            return
        report.add(
            "live.envelope",
            "pass",
            "upstream returned "
            + str(error.get("code"))
            + "; error envelope is well-formed (exit "
            + str(run.exit_code)
            + ")",
        )
        report.add(
            "live.upstream",
            "warn",
            "the source did not serve data: " + str(error.get("message", ""))[:120],
            hint="A tool problem this is not - but the live cache check cannot run.",
        )
        return

    missing = [k for k in REQUIRED_ENVELOPE_KEYS if k not in payload]
    if missing:
        report.add(
            "live.envelope",
            "fail",
            "envelope missing: " + ", ".join(missing),
            hint="Spec section 1 requires: " + ", ".join(REQUIRED_ENVELOPE_KEYS),
        )
    else:
        report.add("live.envelope", "pass", "envelope complete (ok=" + str(payload.get("ok")) + ")")

    rows = payload.get("rows")
    count = payload.get("count")
    if isinstance(rows, list) and isinstance(count, int) and count != len(rows):
        report.add(
            "live.count",
            "fail",
            "count=" + str(count) + " but rows has " + str(len(rows)) + " entries",
            hint="Spec section 1: count must equal len(rows).",
        )
    elif isinstance(rows, list):
        report.add("live.count", "pass", "count matches rows (" + str(len(rows)) + ")")

    # A second identical call must be served from the disk cache (spec section 3).
    # A first call that returned nothing proves nothing either way: tools
    # correctly decline to cache empty or failed responses, so grading the
    # cache on one would report a defect that is really an absent fixture.
    if isinstance(rows, list) and not rows:
        report.add(
            "live.cache",
            "skip",
            "first call returned no rows, so a cache hit cannot be demonstrated",
            hint="Pick an example that returns data to exercise the cache.",
        )
        return

    again = invoke(tool, [*args, "--format", "json"], timeout=timeout, prefer=prefer)
    again_payload = again.json()
    if isinstance(again_payload, dict):
        if again_payload.get("cached") is True:
            report.add("live.cache", "pass", "second identical call reports cached=true")
        else:
            report.add(
                "live.cache",
                "warn",
                "second identical call reports cached=" + repr(again_payload.get("cached")),
                hint="Spec section 3: the disk cache must survive across processes.",
            )


def _first_example(manifest: dict[str, Any]) -> str | None:
    """Pick an example worth grading the envelope and cache against.

    It has to be a command that actually calls the upstream API. Grading
    ``cache stats`` would be meaningless - it is local, so it is correctly
    never "cached", and the audit would report a cache failure that is really
    an audit bug. A command opts out by declaring ``"network": false``;
    otherwise we fall back to a name denylist for tools that do not declare it.
    """
    fallback: str | None = None
    for command in manifest.get("commands") or []:
        if not isinstance(command, dict):
            continue
        example = next(
            (e.strip() for e in command.get("examples") or [] if isinstance(e, str) and e.strip()),
            None,
        )
        if example is None:
            continue
        declared = command.get("network")
        if declared is False:
            continue
        # Names may be full paths ("cache stats", "series get"), so match on
        # the leading token rather than the whole string.
        head = str(command.get("name", "")).lower().split(" ")[0]
        local_by_name = head in LOCAL_COMMANDS
        if declared is True or not local_by_name:
            return example
        fallback = fallback or example
    return fallback


# Commands that answer from local state, so a "cached" flag is meaningless.
LOCAL_COMMANDS = {
    "cache",
    "describe",
    "guide",
    "config",
    "completion",
    "serve",
    "mcp-config",
    "prompt",
    "prompts",
    "filter-guide",
    "examples",
    "models",
    "version",
}


def _example_args(example: str, script: str) -> list[str] | None:
    """Strip the program name off a documented example, keeping its arguments.

    Examples are written the way a human would type them, so they may be piped
    or redirected; everything from the first shell metacharacter on is dropped
    because the runner executes argv directly rather than through a shell.
    """
    for meta in ("|", ">", "&&", ";"):
        if meta in example:
            example = example.split(meta, 1)[0]
    try:
        parts = shlex.split(example)
    except ValueError:
        return None
    if not parts:
        return None
    head = parts[0]
    if head == script or head.endswith("/" + script) or head.endswith(script + ".exe"):
        parts = parts[1:]
    # Formats and output paths are supplied by the caller, so drop any the
    # example pinned - otherwise we would grade the envelope of a CSV file.
    cleaned: list[str] = []
    skip_next = False
    for part in parts:
        if skip_next:
            skip_next = False
            continue
        if part in ("-f", "--format", "-o", "--output"):
            skip_next = True
            continue
        if part.startswith("--format=") or part.startswith("--output="):
            continue
        cleaned.append(part)
    return cleaned or None
