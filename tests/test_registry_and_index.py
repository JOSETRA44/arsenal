"""Registry resolution, invocation bookkeeping, and index search."""

from __future__ import annotations

import json
import sys

import pytest

from arsenal import index
from arsenal.cli import build_manifest, build_parser
from arsenal.registry import BY_NAME, TOOLS
from arsenal.runner import Invocation


def test_every_tool_name_is_unique_and_indexed():
    names = [t.name for t in TOOLS]
    assert len(names) == len(set(names))
    assert set(BY_NAME) == set(names)


def test_registry_points_at_directories_that_exist():
    # A typo in project_dir would silently downgrade a tool to "missing".
    missing = [t.name for t in TOOLS if not t.path.is_dir()]
    assert missing == [], "registry references non-existent directories: " + str(missing)


def test_source_preference_reorders_candidates():
    tool = BY_NAME["undata"]
    installed_first = tool.candidates("installed")
    source_first = tool.candidates("source")
    if len(installed_first) > 1:
        assert installed_first != source_first
        assert source_first[0] != installed_first[0]


def test_invocation_json_returns_none_for_table_output():
    run = Invocation(tool="t", argv=[], exit_code=0, stdout="a plain table\n", stderr="")
    assert run.json() is None


def test_invocation_json_parses_an_envelope():
    run = Invocation(tool="t", argv=[], exit_code=0, stdout='{"ok": true}', stderr="")
    assert run.json() == {"ok": True}


def test_invocation_jsonl_skips_blank_lines():
    run = Invocation(tool="t", argv=[], exit_code=0, stdout='{"a":1}\n\n{"a":2}\n', stderr="")
    assert run.jsonl() == [{"a": 1}, {"a": 2}]


def test_invocation_jsonl_raises_on_a_malformed_line():
    run = Invocation(tool="t", argv=[], exit_code=0, stdout='{"a":1}\nnope\n', stderr="")
    with pytest.raises(ValueError, match="line 2"):
        run.jsonl()


def test_exit_meaning_names_known_codes_and_flags_unknown_ones():
    assert Invocation("t", [], 4, "", "").exit_meaning == "auth"
    assert "undefined" in Invocation("t", [], 99, "", "").exit_meaning


# --- index -----------------------------------------------------------------

DOCUMENT = {
    "index_version": index.INDEX_VERSION,
    "built_at": "2026-08-20T00:00:00Z",
    "tools": [
        {
            "tool": "openalex",
            "available": True,
            "summary": "scholarly works",
            "tags": ["academic", "citations"],
            "auth": "optional",
            "manifest": {
                "commands": [
                    {
                        "name": "search-works",
                        "summary": "Search works",
                        "row_fields": ["cited_by_count", "title"],
                        "examples": ["openalex search-works x"],
                    },
                    {"name": "get-author", "summary": "Author profile", "row_fields": ["h_index"]},
                ]
            },
        },
        {
            "tool": "bcrp",
            "available": True,
            "summary": "Peru macro series",
            "tags": ["economics", "peru"],
            "auth": "none",
            "manifest": {"commands": [{"name": "series", "summary": "Fetch a time series"}]},
        },
    ],
}


def test_search_matches_a_row_field():
    # "h_index" appears only as a row field - this is the case that makes the
    # index worth building at all.
    hits = index.search(DOCUMENT, "h_index")
    assert [h["command"] for h in hits] == ["get-author"]


def test_search_matches_a_tool_tag_and_returns_all_its_commands():
    hits = index.search(DOCUMENT, "peru")
    assert {h["tool"] for h in hits} == {"bcrp"}


def test_search_is_case_insensitive():
    assert index.search(DOCUMENT, "CITED_BY_COUNT")


def test_search_returns_empty_for_no_match():
    assert index.search(DOCUMENT, "zzzz") == []


def test_search_surfaces_auth_so_a_caller_knows_the_cost():
    hits = index.search(DOCUMENT, "cited_by_count")
    assert hits[0]["auth"] == "optional"


def test_entry_round_trips_through_dict():
    entry = index.entries(DOCUMENT)[0]
    assert index.Entry.from_dict(entry.to_dict()).tool == entry.tool


# --- the arsenal's own manifest --------------------------------------------


def test_manifest_lists_every_registered_subcommand():
    parser = build_parser()
    registered = set()
    for action in parser._subparsers._group_actions:
        registered |= set(getattr(action, "choices", {}))
    described = {c["name"] for c in build_manifest()["commands"]}
    assert described == registered


def test_manifest_declares_the_five_required_formats():
    assert set(build_manifest()["formats"]) >= {"table", "json", "jsonl", "csv", "md"}


def test_manifest_documents_all_seven_exit_codes():
    assert set(build_manifest()["exit_codes"]) == {str(c) for c in range(7)}


def test_manifest_is_json_serialisable():
    json.dumps(build_manifest())


def test_every_manifest_command_carries_an_example():
    for command in build_manifest()["commands"]:
        assert command["examples"], command["name"] + " has no example"


def test_workspace_env_override_wins(monkeypatch, tmp_path):
    # Once the arsenal is installed as a tool its package lives nowhere near the
    # projects, so an explicit override has to be honoured.
    import importlib

    from arsenal import registry

    monkeypatch.setenv("ARSENAL_WORKSPACE", str(tmp_path))
    reloaded = importlib.reload(registry)
    try:
        assert reloaded.WORKSPACE == tmp_path.resolve()
    finally:
        monkeypatch.delenv("ARSENAL_WORKSPACE", raising=False)
        importlib.reload(registry)


def test_workspace_is_found_by_the_spec_file():
    from arsenal.registry import SPEC_FILE, WORKSPACE

    assert (WORKSPACE / SPEC_FILE).is_file(), (
        "workspace resolved to " + str(WORKSPACE) + ", which has no " + SPEC_FILE
    )
