"""The audit must grade a manifest correctly without invoking anything real."""

from __future__ import annotations

from typing import Any

import pytest

from arsenal import doctor
from arsenal.doctor import Report

GOOD_MANIFEST: dict[str, Any] = {
    "name": "openalex",
    "version": "0.2.0",
    "source": {"api": "OpenAlex", "base_url": "https://api.openalex.org", "auth": "optional"},
    "formats": ["table", "json", "jsonl", "csv", "md"],
    "exit_codes": {str(c): "x" for c in range(7)},
    "commands": [
        {
            "name": "search-works",
            "summary": "Search scholarly works",
            "row_fields": ["id", "title", "cited_by_count"],
            "examples": ["openalex search-works 'graphs' -f jsonl"],
        }
    ],
}


def statuses(report: Report) -> dict[str, str]:
    return {f.check: f.status for f in report.findings}


def test_good_manifest_passes_every_check():
    report = Report(tool="openalex")
    doctor._check_manifest(report, GOOD_MANIFEST)
    assert report.compliant
    assert set(statuses(report).values()) == {"pass"}


def test_missing_format_fails():
    manifest = {**GOOD_MANIFEST, "formats": ["table", "json"]}
    report = Report(tool="t")
    doctor._check_manifest(report, manifest)
    assert statuses(report)["formats"] == "fail"
    assert "jsonl" in report.failed[0].detail or "jsonl" in str(report.failed)


def test_extra_format_is_allowed():
    manifest = {**GOOD_MANIFEST, "formats": [*GOOD_MANIFEST["formats"], "parquet"]}
    report = Report(tool="t")
    doctor._check_manifest(report, manifest)
    assert statuses(report)["formats"] == "pass"


def test_undocumented_exit_code_warns_rather_than_fails():
    # A tool with no network genuinely has no code 6 path; that is a doc gap.
    manifest = {**GOOD_MANIFEST, "exit_codes": {"0": "ok", "2": "usage"}}
    report = Report(tool="t")
    doctor._check_manifest(report, manifest)
    assert statuses(report)["exit_codes"] == "warn"
    assert report.compliant


def test_missing_manifest_keys_fail():
    manifest = {k: v for k, v in GOOD_MANIFEST.items() if k != "version"}
    report = Report(tool="t")
    doctor._check_manifest(report, manifest)
    assert statuses(report)["manifest.keys"] == "fail"


def test_command_without_summary_fails():
    manifest = {**GOOD_MANIFEST, "commands": [{"name": "orphan"}]}
    report = Report(tool="t")
    doctor._check_manifest(report, manifest)
    assert statuses(report)["commands"] == "fail"


def test_no_examples_warns():
    manifest = {**GOOD_MANIFEST, "commands": [{"name": "c", "summary": "s"}]}
    report = Report(tool="t")
    doctor._check_manifest(report, manifest)
    assert statuses(report)["examples"] == "warn"
    assert report.compliant


def test_score_excludes_skips():
    report = Report(tool="t")
    report.add("a", "pass", "")
    report.add("b", "fail", "")
    report.add("c", "skip", "")
    assert report.score == (1, 2)


@pytest.mark.parametrize(
    "example,expected",
    [
        ("openalex search-works 'graph nets'", ["search-works", "graph nets"]),
        ("openalex search-works x -f jsonl", ["search-works", "x"]),
        ("openalex search-works x --format=csv", ["search-works", "x"]),
        ("openalex list | jq .rows", ["list"]),
        ("openalex export -o out.csv", ["export"]),
        ("/usr/local/bin/openalex get-work W123", ["get-work", "W123"]),
    ],
)
def test_example_args_strips_program_shell_and_pinned_format(example, expected):
    assert doctor._example_args(example, "openalex") == expected


def test_example_args_returns_none_for_bare_program_name():
    assert doctor._example_args("openalex", "openalex") is None


def test_first_example_finds_the_first_non_empty_one():
    manifest = {
        "commands": [
            {"name": "a", "summary": "s", "examples": []},
            {"name": "b", "summary": "s", "examples": ["  ", "tool b --x"]},
        ]
    }
    assert doctor._first_example(manifest) == "tool b --x"


def test_report_to_dict_is_json_shaped():
    report = Report(tool="t")
    report.add("a", "pass", "fine")
    payload = report.to_dict()
    assert payload["tool"] == "t"
    assert payload["compliant"] is True
    assert payload["findings"][0]["check"] == "a"


def test_local_command_example_is_not_chosen_for_the_live_check():
    # `cache stats` is local, so it is correctly never "cached"; grading it
    # would report an audit bug as a tool defect.
    manifest = {
        "commands": [
            {"name": "cache", "summary": "s", "examples": ["t cache stats -f json"]},
            {"name": "search", "summary": "s", "examples": ["t search x"]},
        ]
    }
    assert doctor._first_example(manifest) == "t search x"


def test_network_false_opts_a_command_out_even_with_an_unknown_name():
    manifest = {
        "commands": [
            {"name": "catalog", "summary": "s", "network": False, "examples": ["t catalog"]},
            {"name": "series", "summary": "s", "examples": ["t series X"]},
        ]
    }
    assert doctor._first_example(manifest) == "t series X"


def test_a_local_example_is_still_used_when_it_is_the_only_one():
    manifest = {"commands": [{"name": "cache", "summary": "s", "examples": ["t cache stats"]}]}
    assert doctor._first_example(manifest) == "t cache stats"
