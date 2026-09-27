"""Install every server, and run every server's tests, from one place.

Seven projects across three ecosystems means seven different install
incantations and seven different test runners. Remembering which is which is
exactly the friction that stops someone verifying their setup, so this reduces
all of it to ``arsenal install`` and ``arsenal test``.

Both report per-project rather than aborting on the first failure: when six
work and one does not, that is far more useful than a single stack trace.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Callable, Iterable

from .registry import TOOLS, Tool


@dataclass
class StepResult:
    """One command run against one project."""

    tool: str
    step: str
    ok: bool
    exit_code: int
    seconds: float
    detail: str = ""

    def row(self) -> dict[str, object]:
        return {
            "tool": self.tool,
            "step": self.step,
            "ok": self.ok,
            "exit_code": self.exit_code,
            "seconds": round(self.seconds, 1),
            "detail": self.detail,
        }


def resolve(argv: list[str]) -> list[str]:
    """Replace argv[0] with its absolute path.

    On Windows the runners are shims — ``npm.cmd``, ``npx.cmd`` — and
    ``subprocess`` without a shell will not find them by bare name, reporting a
    perfectly installed tool as missing. ``shutil.which`` applies PATHEXT and
    returns the real file, which works identically on POSIX.
    """
    if not argv:
        return argv
    found = shutil.which(argv[0])
    return [found, *argv[1:]] if found else argv


def _run(tool: Tool, step: str, argv: list[str], timeout: int) -> StepResult:
    started = time.monotonic()
    argv = resolve(argv)
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except FileNotFoundError:
        return StepResult(
            tool.name, step, False, 127, time.monotonic() - started,
            f"{argv[0]} is not installed or not on PATH",
        )
    except subprocess.TimeoutExpired:
        return StepResult(
            tool.name, step, False, 124, time.monotonic() - started,
            f"timed out after {timeout}s",
        )

    elapsed = time.monotonic() - started
    ok = proc.returncode == 0
    detail = "" if ok else _explain(proc.stdout, proc.stderr)
    return StepResult(tool.name, step, ok, proc.returncode, elapsed, detail)


def _explain(stdout: str, stderr: str) -> str:
    """The most useful line from a failed run.

    Test runners put the summary last and tracebacks put the cause last, so the
    tail is usually the line worth showing. Preferring stderr matters because a
    crashed process often writes nothing at all to stdout.
    """
    for stream in (stderr, stdout):
        lines = [line.strip() for line in stream.splitlines() if line.strip()]
        if lines:
            return " | ".join(lines[-2:])[:220]
    return "no output"


def _summarise(stdout: str) -> str:
    """A one-line pass/fail summary from a test runner's output."""
    for line in reversed([l.strip() for l in stdout.splitlines() if l.strip()]):
        lowered = line.lower()
        if any(word in lowered for word in ("passed", "failed", "superado", "tests ")):
            return line[:120]
    return ""


def _install_lock_failure(result: StepResult) -> bool:
    """Did this install fail because a running server held the console script?

    `uv tool install --force` deletes the old Scripts directory before writing
    the new one. If an MCP server is running from that directory, Windows
    refuses the delete and uv aborts *after* the removal has partly happened —
    leaving the launcher on PATH with no package behind it. The tool then fails
    with "No module named ...", which reads like a code bug and is not one.
    """
    return result.exit_code != 0 and (
        "Acceso denegado" in result.detail
        or "os error 5" in result.detail
        or "Access is denied" in result.detail
        or "failed to remove" in result.detail
    )


def install_all(
    tools: Iterable[Tool] = TOOLS,
    *,
    timeout: int = 900,
    on_step: Callable[[str], None] | None = None,
) -> list[StepResult]:
    """Install every project so its CLI and MCP server land on PATH."""
    results: list[StepResult] = []
    for tool in tools:
        if on_step:
            on_step(f"installing {tool.name}...")
        result = _run(tool, "install", tool.install_command(), timeout)
        if _install_lock_failure(result):
            # Say what actually happened, and warn that the tool may now be
            # half-installed — silence here previously cost an hour of
            # debugging a "No module named" that had nothing to do with code.
            result = StepResult(
                tool.name,
                "install",
                False,
                result.exit_code,
                result.seconds,
                "a running process holds this tool's console script, so the install was "
                "aborted mid-way and the installed copy may now be BROKEN. Stop the "
                f"{tool.mcp_script or tool.script} MCP server (or close the client using "
                "it) and re-run. Original error: " + result.detail[:120],
            )
        results.append(result)

        build = tool.build_command()
        if build is not None:
            if on_step:
                on_step(f"building {tool.name}...")
            results.append(_run(tool, "build", build, timeout))
    return results


def test_all(
    tools: Iterable[Tool] = TOOLS,
    *,
    timeout: int = 1800,
    on_step: Callable[[str], None] | None = None,
) -> list[StepResult]:
    """Run every project's own test suite."""
    results: list[StepResult] = []
    for tool in tools:
        if on_step:
            on_step(f"testing {tool.name}...")
        started = time.monotonic()
        argv = resolve(tool.test_command())
        try:
            proc = subprocess.run(
                argv, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=timeout,
            )
        except FileNotFoundError:
            results.append(StepResult(
                tool.name, "test", False, 127, time.monotonic() - started,
                f"{argv[0]} is not installed or not on PATH",
            ))
            continue
        except subprocess.TimeoutExpired:
            results.append(StepResult(
                tool.name, "test", False, 124, time.monotonic() - started,
                f"timed out after {timeout}s",
            ))
            continue

        elapsed = time.monotonic() - started
        ok = proc.returncode == 0
        detail = _summarise(proc.stdout) if ok else _explain(proc.stdout, proc.stderr)
        results.append(StepResult(tool.name, "test", ok, proc.returncode, elapsed, detail))
    return results
