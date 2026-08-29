"""``arsenal`` - one entry point across every research CLI in this workspace.

    arsenal list                    which tools exist, and are they installed
    arsenal search <term>           which command anywhere answers this question
    arsenal index --refresh         rebuild the aggregated manifest cache
    arsenal doctor [--live]         grade every tool against ARSENAL-SPEC.md
    arsenal run <tool> [args...]    passthrough to a tool, streams its output
    arsenal describe --json         the arsenal's own manifest

The arsenal obeys the contract it audits: same flags, same envelope, same exit
codes. Auditing a spec you do not follow yourself is how specs rot.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from . import __version__, doctor, index, lifecycle, render
from .registry import BY_NAME, TOOLS, WORKSPACE_FOUND, WORKSPACE_HINT
from .render import (
    EXIT_API,
    EXIT_NOT_FOUND,
    EXIT_OK,
    EXIT_USAGE,
    FORMATS,
)
from .runner import ToolUnavailable, invoke


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arsenal",
        description="Query, audit and drive every research CLI in this workspace.",
    )
    parser.add_argument("--version", action="version", version="arsenal " + __version__)
    _add_global_flags(parser)

    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p = sub.add_parser("list", help="List the registered research tools and their availability.")
    _add_global_flags(p)

    p = sub.add_parser("search", help="Find the command, in any tool, that answers a question.")
    p.add_argument("term", help="Substring matched against tags, summaries and row fields.")
    p.add_argument("--refresh", action="store_true", help="Rebuild the index before searching.")
    p.add_argument(
        "--prefer",
        choices=("source", "installed"),
        default="source",
        help="Probe the working tree ('source', the default) or the copy on PATH.",
    )
    _add_global_flags(p)

    p = sub.add_parser("index", help="Show the aggregated manifest index.")
    p.add_argument("--refresh", action="store_true", help="Re-probe every tool.")
    p.add_argument(
        "--prefer",
        choices=("source", "installed"),
        default="source",
        help="Probe the working tree ('source', the default) or the copy on PATH.",
    )
    _add_global_flags(p)

    p = sub.add_parser("doctor", help="Grade every tool against ARSENAL-SPEC.md.")
    p.add_argument("tools", nargs="*", help="Tool names to audit (default: all).")
    p.add_argument(
        "--live",
        action="store_true",
        help="Also run one real example per tool to verify the envelope and cache "
        "(costs network calls and API quota).",
    )
    p.add_argument("--timeout", type=int, default=120, help="Per-invocation timeout in seconds.")
    p.add_argument(
        "--mcp",
        action="store_true",
        help="Also speak the MCP protocol to each server (initialize + tools/list). "
        "This is what an MCP client actually does, and the CLI checks do not cover it.",
    )
    p.add_argument(
        "--prefer",
        choices=("installed", "source"),
        default="source",
        help="Audit the working tree ('source', the default) or the copy installed "
        "on PATH ('installed'). An installed script is a snapshot from whenever it "
        "was last installed, so it will not reflect uncommitted work.",
    )
    _add_global_flags(p)

    p = sub.add_parser(
        "install",
        help="Install every server so its CLI and MCP server land on PATH.",
    )
    p.add_argument("tools", nargs="*", help="Tool names to install (default: all).")
    p.add_argument("--timeout", type=int, default=900, help="Per-project timeout in seconds.")
    _add_global_flags(p)

    p = sub.add_parser("test", help="Run every server's own test suite.")
    p.add_argument("tools", nargs="*", help="Tool names to test (default: all).")
    p.add_argument("--timeout", type=int, default=1800, help="Per-project timeout in seconds.")
    _add_global_flags(p)

    p = sub.add_parser(
        "verify",
        help="Install, test, then audit everything — the one command that proves the "
        "whole arsenal works end to end.",
    )
    p.add_argument("--skip-install", action="store_true", help="Assume everything is installed.")
    p.add_argument("--live", action="store_true", help="Include the live API checks.")
    p.add_argument("--timeout", type=int, default=1800, help="Per-project timeout in seconds.")
    _add_global_flags(p)

    p = sub.add_parser(
        "run",
        help="Run a tool, passing every remaining argument straight through.",
    )
    p.add_argument("tool", help="Registered tool name, e.g. 'openalex'.")
    p.add_argument("args", nargs=argparse.REMAINDER, help="Arguments forwarded verbatim.")

    p = sub.add_parser("describe", help="The arsenal's own machine-readable manifest.")
    p.add_argument("--json", action="store_true", help="Emit the manifest as JSON.")
    _add_global_flags(p)

    return parser


def _add_global_flags(parser: argparse.ArgumentParser) -> None:
    """Attach the spec's global flags.

    They are attached to the root *and* each subparser so both ``arsenal -f json
    list`` and ``arsenal list -f json`` work - agents write both, and failing on
    the wrong one is a pointless papercut.
    """
    parser.add_argument("-f", "--format", dest="format", choices=FORMATS, default=None)
    parser.add_argument("-o", "--output", dest="output", metavar="FILE", default=None)
    parser.add_argument("-q", "--quiet", dest="quiet", action="store_true", default=False)
    parser.add_argument("--no-color", dest="no_color", action="store_true", default=False)


def _merge(root: argparse.Namespace, key: str, default: Any) -> Any:
    """Subcommand flags win over root flags; the root value is the fallback."""
    value = getattr(root, key, None)
    return default if value in (None, False) else value


def cmd_list(args: argparse.Namespace) -> int:
    rows = []
    for tool in TOOLS:
        candidates = tool.candidates()
        rows.append(
            {
                "tool": tool.name,
                "status": "installed"
                if candidates and len(candidates[0]) == 1
                else ("source" if candidates else "missing"),
                "auth": tool.auth,
                "runtime": tool.runtime,
                "tags": ", ".join(tool.tags),
                "summary": tool.summary,
            }
        )
    payload = render.envelope("list", rows, {"workspace_tools": len(TOOLS)})
    render.emit(payload, args.format, args.output, title="Research arsenal", quiet=args.quiet)
    return EXIT_OK


def cmd_search(args: argparse.Namespace) -> int:
    document = index.load(refresh=args.refresh, prefer=args.prefer)
    hits = index.search(document, args.term)
    if not hits:
        render.note(
            "No command matches " + repr(args.term) + ". Try `arsenal index --refresh` "
            "if you have just installed or changed a tool.",
            quiet=args.quiet,
        )
    payload = render.envelope("search", hits, {"term": args.term}, meta={"term": args.term})
    render.emit(payload, args.format, args.output, title="Matches for " + args.term, quiet=args.quiet)
    return EXIT_OK


def cmd_index(args: argparse.Namespace) -> int:
    document = index.load(refresh=args.refresh, prefer=args.prefer)
    rows = []
    for entry in index.entries(document):
        manifest = entry.manifest or {}
        rows.append(
            {
                "tool": entry.tool,
                "available": entry.available,
                "version": manifest.get("version", ""),
                "commands": len(entry.commands),
                "formats": ", ".join(manifest.get("formats") or []),
                "error": entry.error or "",
            }
        )
    payload = render.envelope(
        "index", rows, document, meta={"built_at": document.get("built_at")}
    )
    render.emit(payload, args.format, args.output, title="Manifest index", quiet=args.quiet)
    return EXIT_OK


def cmd_doctor(args: argparse.Namespace) -> int:
    selected = TOOLS
    if args.tools:
        unknown = [t for t in args.tools if t not in BY_NAME]
        if unknown:
            return render.fail(
                "doctor",
                "usage",
                "unknown tool(s): " + ", ".join(unknown),
                "Known tools: " + ", ".join(BY_NAME),
                args.format,
                EXIT_USAGE,
            )
        selected = tuple(BY_NAME[t] for t in args.tools)

    reports = []
    rows = []
    for tool in selected:
        render.note("auditing " + tool.name + " (" + args.prefer + ")...", quiet=args.quiet)
        report = doctor.audit(
            tool, live=args.live, timeout=args.timeout, prefer=args.prefer,
            mcp=getattr(args, "mcp", False),
        )
        reports.append(report)
        passed, graded = report.score
        rows.append(
            {
                "tool": report.tool,
                "compliant": report.compliant,
                "score": str(passed) + "/" + str(graded),
                "failed": len(report.failed),
                "warned": len(report.warned),
                "issues": "; ".join(
                    f.check + ": " + _one_line(f.detail, 110) for f in report.failed[:3]
                ),
            }
        )

    payload = render.envelope(
        "doctor",
        rows,
        {"reports": [r.to_dict() for r in reports]},
        meta={
            "live": args.live,
            "mcp": getattr(args, "mcp", False),
            "prefer": args.prefer,
            "audited": len(reports),
        },
    )
    render.emit(payload, args.format, args.output, title="Spec conformance", quiet=args.quiet)

    if args.format == "table" and args.output is None and not args.quiet:
        _print_doctor_detail(reports, no_color=args.no_color)

    # A non-compliant arsenal is an API-level failure: the tools exist but do
    # not honour the contract callers were promised.
    return EXIT_API if any(not r.compliant for r in reports) else EXIT_OK


def _one_line(text: str, limit: int) -> str:
    """Collapse a finding's detail for tabular display.

    Tools quote upstream error output verbatim, which is frequently multi-line
    and sometimes contains box-drawing characters; either would wreck a table.
    The untruncated text stays in the JSON report.
    """
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def _print_doctor_detail(reports: list[doctor.Report], *, no_color: bool) -> None:
    marks = {"pass": ("ok  ", "green"), "fail": ("FAIL", "red"), "warn": ("warn", "yellow"), "skip": ("skip", "dim")}
    for report in reports:
        print()
        print(render.colored(report.tool, "bold", no_color=no_color))
        for finding in report.findings:
            label, color = marks[finding.status]
            detail = _one_line(finding.detail, 160)
            print("  " + render.colored(label, color, no_color=no_color) + " " + finding.check + ": " + detail)
            if finding.hint and finding.status in ("fail", "warn"):
                print(render.colored("       -> " + finding.hint, "dim", no_color=no_color))


def _selected(args: argparse.Namespace) -> tuple[Any, ...] | None:
    """Resolve the tool names on the command line, or every tool."""
    names = getattr(args, "tools", None) or []
    if not names:
        return TOOLS
    unknown = [n for n in names if n not in BY_NAME]
    if unknown:
        render.fail(
            args.command,
            "usage",
            "unknown tool(s): " + ", ".join(unknown),
            "Known tools: " + ", ".join(BY_NAME),
            args.format,
            EXIT_USAGE,
        )
        return None
    return tuple(BY_NAME[n] for n in names)


def _report_steps(args: argparse.Namespace, command: str, results: list) -> int:
    rows = [r.row() for r in results]
    failed = [r for r in results if not r.ok]
    payload = render.envelope(
        command,
        rows,
        {"failed": [r.tool for r in failed]},
        meta={"total": len(results), "failed": len(failed)},
    )
    render.emit(payload, args.format, args.output, title=command.title(), quiet=args.quiet)

    if failed and not args.quiet:
        render.note("")
        for result in failed:
            render.note(f"{result.tool} {result.step}: exit {result.exit_code} — {result.detail}")
    return EXIT_API if failed else EXIT_OK


def cmd_install(args: argparse.Namespace) -> int:
    tools = _selected(args)
    if tools is None:
        return EXIT_USAGE
    results = lifecycle.install_all(
        tools, timeout=args.timeout,
        on_step=None if args.quiet else lambda m: render.note(m),
    )
    return _report_steps(args, "install", results)


def cmd_test(args: argparse.Namespace) -> int:
    tools = _selected(args)
    if tools is None:
        return EXIT_USAGE
    results = lifecycle.test_all(
        tools, timeout=args.timeout,
        on_step=None if args.quiet else lambda m: render.note(m),
    )
    return _report_steps(args, "test", results)


def cmd_verify(args: argparse.Namespace) -> int:
    """Install, test, then audit — the single command that proves the set works.

    Ordered deliberately: installing first means the audit grades what a user
    would actually get, and testing before auditing surfaces a broken build as
    a test failure rather than as a confusing protocol error.
    """
    steps: list = []
    if not args.skip_install:
        steps += lifecycle.install_all(
            TOOLS, timeout=args.timeout,
            on_step=None if args.quiet else lambda m: render.note(m),
        )
    steps += lifecycle.test_all(
        TOOLS, timeout=args.timeout,
        on_step=None if args.quiet else lambda m: render.note(m),
    )

    reports = []
    for tool in TOOLS:
        render.note("auditing " + tool.name + "...", quiet=args.quiet)
        reports.append(
            doctor.audit(tool, live=args.live, timeout=300, prefer="installed", mcp=True)
        )

    rows = [r.row() for r in steps]
    for report in reports:
        passed, graded = report.score
        rows.append({
            "tool": report.tool,
            "step": "audit",
            "ok": report.compliant,
            "exit_code": 0 if report.compliant else 1,
            "seconds": 0,
            "detail": f"{passed}/{graded} checks"
            + ("" if report.compliant else "; " + report.failed[0].detail[:120]),
        })

    broken = [r for r in rows if not r["ok"]]
    payload = render.envelope(
        "verify",
        rows,
        {"reports": [r.to_dict() for r in reports]},
        meta={"steps": len(rows), "failed": len(broken), "live": args.live},
    )
    render.emit(payload, args.format, args.output, title="Verify", quiet=args.quiet)

    if not args.quiet:
        render.note("")
        if broken:
            for row in broken:
                render.note(f"FAILED  {row['tool']} {row['step']}: {row['detail']}")
        else:
            render.note(f"All {len(TOOLS)} servers install, test and audit clean.")
    return EXIT_API if broken else EXIT_OK


def cmd_run(args: argparse.Namespace) -> int:
    tool = BY_NAME.get(args.tool)
    if tool is None:
        return render.fail(
            "run",
            "usage",
            "unknown tool " + repr(args.tool),
            "Known tools: " + ", ".join(BY_NAME),
            "table",
            EXIT_USAGE,
        )
    forwarded = [a for a in args.args if a != "--"]
    try:
        run = invoke(tool, forwarded, timeout=600)
    except ToolUnavailable as exc:
        return render.fail("run", "not_found", str(exc), "", "table", EXIT_NOT_FOUND)
    # Passthrough is verbatim in both directions: the tool's own exit code is
    # the arsenal's, so wrapping never hides a failure from a caller.
    sys.stdout.write(run.stdout)
    sys.stderr.write(run.stderr)
    return run.exit_code


def cmd_describe(args: argparse.Namespace) -> int:
    manifest = build_manifest()
    if args.format == "json" or args.json:
        sys.stdout.write(render.to_json(manifest) + "\n")
        return EXIT_OK
    rows = [
        {"command": c["name"], "summary": c["summary"], "example": (c.get("examples") or [""])[0]}
        for c in manifest["commands"]
    ]
    payload = render.envelope("describe", rows, manifest)
    render.emit(payload, args.format, args.output, title="arsenal " + __version__, quiet=args.quiet)
    return EXIT_OK


def build_manifest() -> dict[str, Any]:
    """The arsenal's manifest, derived from its own parser like every tool's."""
    parser = build_parser()
    commands: list[dict[str, Any]] = []
    examples = {
        "list": ["arsenal list -f json"],
        "search": ["arsenal search 'citation' -f json"],
        "index": ["arsenal index --refresh -f json"],
        "doctor": ["arsenal doctor --live --mcp -f json -o audit.json"],
        "install": ["arsenal install", "arsenal install openalex bcrp"],
        "test": ["arsenal test", "arsenal test undata -f json"],
        "verify": ["arsenal verify", "arsenal verify --skip-install --live"],
        "run": ["arsenal run openalex search-works 'graph neural networks' -f jsonl"],
        "describe": ["arsenal describe --json"],
    }
    row_fields = {
        "list": ["tool", "status", "auth", "runtime", "tags", "summary"],
        "search": ["tool", "command", "summary", "auth", "row_fields", "example"],
        "index": ["tool", "available", "version", "commands", "formats", "error"],
        "doctor": ["tool", "compliant", "score", "failed", "warned", "issues"],
        "install": ["tool", "step", "ok", "exit_code", "seconds", "detail"],
        "test": ["tool", "step", "ok", "exit_code", "seconds", "detail"],
        "verify": ["tool", "step", "ok", "exit_code", "seconds", "detail"],
        "describe": ["command", "summary", "example"],
    }
    for action in parser._subparsers._group_actions if parser._subparsers else []:
        for name, sub in getattr(action, "choices", {}).items():
            arguments = []
            options = []
            for param in sub._actions:
                if param.dest in ("help", "version"):
                    continue
                entry = {
                    "name": param.dest if not param.option_strings else param.option_strings[-1],
                    "type": "flag" if param.nargs == 0 else "string",
                    "required": bool(param.required),
                    "default": param.default,
                    "help": param.help or "",
                }
                (options if param.option_strings else arguments).append(entry)
            commands.append(
                {
                    "name": name,
                    "summary": (sub.description or "").strip() or name,
                    "arguments": arguments,
                    "options": options,
                    "row_fields": row_fields.get(name, []),
                    "supports_all": False,
                    "examples": examples.get(name, []),
                }
            )
    return {
        "name": "arsenal",
        "version": __version__,
        "source": {
            "api": "local",
            "base_url": None,
            "auth": "none",
            "description": "Aggregates the research CLIs registered in registry.py.",
        },
        "formats": list(FORMATS),
        "exit_codes": {
            "0": "ok",
            "1": "one or more tools are not spec-compliant",
            "2": "usage error",
            "3": "tool not installed",
            "4": "n/a - the arsenal itself needs no credentials",
            "5": "n/a - the arsenal itself makes no rate-limited calls",
            "6": "n/a - the arsenal itself makes no network calls",
        },
        "commands": commands,
    }


def _force_utf8_streams() -> None:
    """Make stdout/stderr UTF-8 regardless of the console code page.

    Windows consoles default to cp1252, which cannot encode the accented text
    that comes back from Peruvian and UN data sources - without this, printing
    a perfectly good result dies with UnicodeEncodeError. Reconfiguring is
    safe on POSIX too, where the streams are already UTF-8.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _force_utf8_streams()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return EXIT_USAGE

    # Every command resolves tools through the registry, so a mislocated
    # workspace would otherwise show up as "everything is missing".
    if not WORKSPACE_FOUND and not getattr(args, "quiet", False):
        render.note(WORKSPACE_HINT)

    # Root-level flags are parsed into the same namespace, so normalise here
    # rather than in every command.
    if args.command != "run":
        args.format = _merge(args, "format", "table")
        args.output = Path(args.output) if getattr(args, "output", None) else None

    handlers = {
        "list": cmd_list,
        "search": cmd_search,
        "index": cmd_index,
        "doctor": cmd_doctor,
        "install": cmd_install,
        "test": cmd_test,
        "verify": cmd_verify,
        "run": cmd_run,
        "describe": cmd_describe,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
