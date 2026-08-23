"""Invoke a registered CLI and interpret its result per the arsenal spec.

Everything the arsenal does to a tool goes through :func:`invoke`, so the
resolution order (installed script → source checkout), the timeout, and the
"which candidate actually worked" bookkeeping live in exactly one place.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any

from .registry import Tool

DEFAULT_TIMEOUT = 120

# Spec section 2. Kept here rather than in the spec-checking code because the
# runner needs to name an exit code even when no audit is running.
EXIT_MEANINGS: dict[int, str] = {
    0: "ok",
    1: "api",
    2: "usage",
    3: "not_found",
    4: "auth",
    5: "rate_limit",
    6: "network",
}


class ToolUnavailable(RuntimeError):
    """The tool is neither installed nor present as a source checkout."""


@dataclass
class Invocation:
    """The outcome of running one CLI once."""

    tool: str
    argv: list[str]
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def exit_meaning(self) -> str:
        return EXIT_MEANINGS.get(self.exit_code, f"undefined({self.exit_code})")

    def json(self) -> Any | None:
        """Parse stdout as JSON, or ``None`` if it is not valid JSON.

        Tools legitimately emit non-JSON on stdout in ``table`` mode, so a parse
        failure is a fact about the output, never an exception here.
        """
        text = self.stdout.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def jsonl(self) -> list[Any]:
        """Parse stdout as JSON Lines, skipping blank lines.

        Raises ``ValueError`` on the first malformed line: unlike ``json()``,
        a caller asking for JSONL has already committed to that format.
        """
        rows: list[Any] = []
        for i, line in enumerate(self.stdout.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"line {i} is not valid JSON: {exc}") from exc
        return rows


def resolve(tool: Tool, prefer: str = "installed") -> list[str]:
    """First working argv prefix for ``tool``."""
    candidates = tool.candidates(prefer)
    if not candidates:
        raise ToolUnavailable(
            f"'{tool.name}' is not installed and {tool.path} is not a usable checkout. "
            f"Install it with:  uv tool install {tool.path}"
        )
    return candidates[0]


def invoke(
    tool: Tool,
    args: list[str],
    *,
    timeout: int = DEFAULT_TIMEOUT,
    env: dict[str, str] | None = None,
    prefer: str = "installed",
) -> Invocation:
    """Run ``tool`` with ``args`` and capture everything about the outcome.

    Candidates are tried in order until one gets far enough to actually run the
    tool. A launcher that fails *before* reaching it - uv unable to rebuild a
    locked venv, a missing interpreter - is not the tool's answer, so falling
    through to the next candidate reports the tool rather than the plumbing.
    """
    candidates = tool.candidates(prefer)
    if not candidates:
        resolve(tool, prefer)  # raises ToolUnavailable with the useful message
    last: Invocation | None = None
    for prefix in candidates:
        last = _run_once(tool, prefix, args, timeout=timeout, env=env)
        if not _launcher_failed(last):
            return last
    assert last is not None
    return last


# Signatures of a launcher failing before the tool ever ran.
_LAUNCHER_ERRORS = (
    "failed to remove file",
    "No solution found when resolving",
    "error: Failed to spawn",
    "No `project` table found",
)


def _launcher_failed(run: Invocation) -> bool:
    return run.exit_code != 0 and any(sig in run.stderr for sig in _LAUNCHER_ERRORS)


def _run_once(
    tool: Tool,
    prefix: list[str],
    args: list[str],
    *,
    timeout: int,
    env: dict[str, str] | None,
) -> Invocation:
    argv = [*prefix, *args]
    run_env = {**os.environ, **(env or {})}
    # Tools honour NO_COLOR per the spec; forcing it keeps captured stdout free
    # of escape sequences that would otherwise break JSON parsing.
    run_env.setdefault("NO_COLOR", "1")
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=run_env,
        )
    except subprocess.TimeoutExpired as exc:
        return Invocation(
            tool=tool.name,
            argv=argv,
            exit_code=124,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
            timed_out=True,
        )
    return Invocation(
        tool=tool.name,
        argv=argv,
        exit_code=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )
