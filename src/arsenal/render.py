"""Output rendering for the arsenal CLI.

The arsenal obeys the same output contract it audits, so this module is a
zero-dependency implementation of ARSENAL-SPEC section 1: one envelope, five
formats, data on stdout and notes on stderr.
"""

from __future__ import annotations

import csv
import io
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Sequence

FORMATS = ("table", "json", "jsonl", "csv", "md")

EXIT_OK = 0
EXIT_API = 1
EXIT_USAGE = 2
EXIT_NOT_FOUND = 3
EXIT_AUTH = 4
EXIT_RATE_LIMIT = 5
EXIT_NETWORK = 6


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def envelope(
    command: str,
    rows: Sequence[dict[str, Any]],
    data: Any = None,
    *,
    meta: dict[str, Any] | None = None,
    cached: bool = False,
) -> dict[str, Any]:
    """Build the success envelope required by spec section 1."""
    rows = list(rows)
    return {
        "ok": True,
        "command": command,
        "source": "arsenal",
        "fetched_at": now(),
        "cached": cached,
        "count": len(rows),
        "meta": meta or {},
        "data": data if data is not None else {},
        "rows": rows,
    }


def error_envelope(command: str, code: str, message: str, hint: str = "") -> dict[str, Any]:
    """Build the error envelope required by spec section 1."""
    return {
        "ok": False,
        "command": command,
        "source": "arsenal",
        "fetched_at": now(),
        "error": {"code": code, "message": message, "hint": hint},
    }


def note(text: str, *, quiet: bool = False) -> None:
    """Write a human note to stderr, where it cannot corrupt a pipeline."""
    if not quiet:
        print(text, file=sys.stderr)


def colored(text: str, color: str, *, no_color: bool = False) -> str:
    if no_color or os.environ.get("NO_COLOR"):
        return text
    codes = {"green": "32", "red": "31", "yellow": "33", "cyan": "36", "dim": "2", "bold": "1"}
    code = codes.get(color)
    return text if code is None else "\033[" + code + "m" + text + "\033[0m"


def _columns(rows: Sequence[dict[str, Any]]) -> list[str]:
    """Union of keys, preserving first-seen order so ragged rows still line up."""
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    return columns


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return format(value, ",.4g")
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    return str(value)


def to_table(rows: Sequence[dict[str, Any]], title: str = "") -> str:
    if not rows:
        return (title + ": no rows.") if title else "no rows."
    columns = _columns(rows)
    cells = [[_cell(row.get(c)) for c in columns] for row in rows]
    widths = [
        max(len(columns[i]), *(len(row[i]) for row in cells)) if cells else len(columns[i])
        for i in range(len(columns))
    ]
    lines = []
    if title:
        lines.append(title)
    lines.append("  ".join(c.ljust(widths[i]) for i, c in enumerate(columns)).rstrip())
    lines.append("  ".join("-" * widths[i] for i in range(len(columns))))
    for row in cells:
        lines.append("  ".join(row[i].ljust(widths[i]) for i in range(len(columns))).rstrip())
    return "\n".join(lines)


def to_md(rows: Sequence[dict[str, Any]]) -> str:
    if not rows:
        return "_no rows_"
    columns = _columns(rows)
    out = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        # A literal pipe would split the cell, so escape it.
        out.append("| " + " | ".join(_cell(row.get(c)).replace("|", "\\|") for c in columns) + " |")
    return "\n".join(out)


def to_csv(rows: Sequence[dict[str, Any]]) -> str:
    if not rows:
        return ""
    columns = _columns(rows)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({c: _cell(row.get(c)) for c in columns})
    return buf.getvalue()


def to_jsonl(rows: Sequence[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(row, ensure_ascii=False, default=str) for row in rows)


def to_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def emit(
    payload: dict[str, Any],
    fmt: str,
    output: Path | None = None,
    *,
    title: str = "",
    quiet: bool = False,
) -> None:
    """Render an envelope in ``fmt`` to ``output`` or stdout."""
    rows = payload.get("rows") or []
    if fmt == "json":
        text = to_json(payload)
    elif fmt == "jsonl":
        text = to_jsonl(rows)
    elif fmt == "csv":
        text = to_csv(rows)
    elif fmt == "md":
        text = to_md(rows)
    else:
        text = to_table(rows, title)

    if output is None:
        sys.stdout.write(text)
        if text and not text.endswith("\n"):
            sys.stdout.write("\n")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + ("" if text.endswith("\n") else "\n"), encoding="utf-8")
        note("Wrote " + str(len(rows)) + " rows -> " + str(output), quiet=quiet)


def fail(command: str, code: str, message: str, hint: str, fmt: str, exit_code: int) -> int:
    """Emit the error envelope and return the process exit code.

    In machine formats the failure goes to stdout as a parseable envelope, so a
    pipeline can inspect it; the human line always goes to stderr.
    """
    payload = error_envelope(command, code, message, hint)
    if fmt in ("json", "jsonl"):
        sys.stdout.write(to_json(payload) + "\n")
    print("error: " + message + (("  hint: " + hint) if hint else ""), file=sys.stderr)
    return exit_code
