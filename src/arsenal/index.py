"""Aggregate every tool's ``describe --json`` manifest into one searchable index.

An agent facing a research question does not know which of seven CLIs answers
it. The index turns "who can give me citation counts?" into a lookup instead of
seven ``--help`` invocations, and it caches the answer so the lookup is free.

The cache is keyed on the tools' *versions*, so upgrading a tool invalidates
only that tool's slice rather than the whole index.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .registry import TOOLS, Tool
from .runner import ToolUnavailable, invoke

INDEX_VERSION = 1


def cache_path() -> Path:
    """Where the aggregated index lives.

    ``platformdirs`` would be tidier, but the arsenal deliberately has zero
    runtime dependencies so it can be run straight from a checkout.
    """
    return Path.home() / ".cache" / "research-arsenal" / "index.json"


@dataclass
class Entry:
    """One tool's slice of the index."""

    tool: str
    available: bool
    summary: str
    tags: tuple[str, ...]
    auth: str
    manifest: dict[str, Any] | None = None
    error: str | None = None

    @property
    def commands(self) -> list[dict[str, Any]]:
        if not self.manifest:
            return []
        return [c for c in self.manifest.get("commands") or [] if isinstance(c, dict)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "available": self.available,
            "summary": self.summary,
            "tags": list(self.tags),
            "auth": self.auth,
            "manifest": self.manifest,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Entry":
        return cls(
            tool=raw["tool"],
            available=raw["available"],
            summary=raw.get("summary", ""),
            tags=tuple(raw.get("tags") or ()),
            auth=raw.get("auth", "none"),
            manifest=raw.get("manifest"),
            error=raw.get("error"),
        )


def probe(tool: Tool, *, timeout: int = 60, prefer: str = "source") -> Entry:
    """Ask one tool to describe itself."""
    base = {
        "tool": tool.name,
        "summary": tool.summary,
        "tags": tool.tags,
        "auth": tool.auth,
    }
    try:
        run = invoke(tool, ["describe", "--json"], timeout=timeout, prefer=prefer)
    except ToolUnavailable as exc:
        return Entry(available=False, error=str(exc), **base)
    if run.exit_code != 0:
        detail = (run.stderr or run.stdout).strip()[:200]
        return Entry(
            available=True,
            error="describe --json exited " + str(run.exit_code) + ": " + detail,
            **base,
        )
    payload = run.json()
    if payload is None:
        return Entry(available=True, error="describe --json emitted non-JSON on stdout", **base)
    if isinstance(payload, dict) and "data" in payload and "ok" in payload:
        payload = payload["data"]
    if not isinstance(payload, dict):
        return Entry(available=True, error="manifest is not a JSON object", **base)
    return Entry(available=True, manifest=payload, **base)


def build(
    tools: Iterable[Tool] = TOOLS, *, timeout: int = 60, prefer: str = "source"
) -> dict[str, Any]:
    """Probe every tool and assemble the index document."""
    entries = [probe(tool, timeout=timeout, prefer=prefer).to_dict() for tool in tools]
    return {
        "index_version": INDEX_VERSION,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tools": entries,
    }


def load(*, refresh: bool = False, timeout: int = 60, prefer: str = "source") -> dict[str, Any]:
    """Return the index, rebuilding it when missing, stale or explicitly refreshed."""
    path = cache_path()
    if not refresh and path.is_file():
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cached = None
        if isinstance(cached, dict) and cached.get("index_version") == INDEX_VERSION:
            return cached
    document = build(timeout=timeout, prefer=prefer)
    save(document)
    return document


def save(document: dict[str, Any]) -> Path:
    path = cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def entries(document: dict[str, Any]) -> list[Entry]:
    return [Entry.from_dict(raw) for raw in document.get("tools") or []]


def search(document: dict[str, Any], term: str) -> list[dict[str, Any]]:
    """Find every command in the arsenal matching ``term``.

    Matching is substring, case-insensitive, across the fields an agent would
    plausibly phrase a question in: the tool's tags and summary, the command
    name and summary, and the row fields the command produces. Row fields
    matter most in practice - "h_index" or "cited_by_count" is exactly how a
    question arrives, and only the manifest knows which command yields it.
    """
    needle = term.lower().strip()
    hits: list[dict[str, Any]] = []
    for entry in entries(document):
        tool_haystack = " ".join([entry.tool, entry.summary, *entry.tags]).lower()
        for command in entry.commands:
            fields = command.get("row_fields") or []
            haystack = " ".join(
                [
                    tool_haystack,
                    str(command.get("name", "")),
                    str(command.get("summary", "")),
                    " ".join(str(f) for f in fields),
                ]
            ).lower()
            if needle in haystack:
                hits.append(
                    {
                        "tool": entry.tool,
                        "command": command.get("name"),
                        "summary": command.get("summary"),
                        "auth": entry.auth,
                        "row_fields": fields,
                        "example": (command.get("examples") or [None])[0],
                    }
                )
    return hits
