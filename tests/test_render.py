"""Rendering must satisfy the same contract the arsenal audits in others."""

from __future__ import annotations

import csv
import io
import json

import pytest

from arsenal import render

ROWS = [
    {"tool": "openalex", "count": 3, "ok": True},
    {"tool": "bcrp", "count": 12, "ok": False, "extra": "ragged"},
]


def test_envelope_has_every_required_key():
    payload = render.envelope("list", ROWS)
    for key in ("ok", "command", "source", "fetched_at", "cached", "count", "meta", "data", "rows"):
        assert key in payload, key
    assert payload["ok"] is True
    assert payload["count"] == len(ROWS)


def test_envelope_count_tracks_rows():
    assert render.envelope("x", [])["count"] == 0
    assert render.envelope("x", ROWS)["count"] == 2


def test_error_envelope_shape():
    payload = render.error_envelope("get", "not_found", "no such series", "check the code")
    assert payload["ok"] is False
    assert payload["error"] == {
        "code": "not_found",
        "message": "no such series",
        "hint": "check the code",
    }


def test_csv_uses_union_of_keys_so_ragged_rows_align():
    text = render.to_csv(ROWS)
    reader = csv.DictReader(io.StringIO(text))
    assert reader.fieldnames == ["tool", "count", "ok", "extra"]
    parsed = list(reader)
    assert parsed[0]["extra"] == ""
    assert parsed[1]["extra"] == "ragged"


def test_jsonl_is_one_object_per_line():
    lines = render.to_jsonl(ROWS).splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["tool"] == "openalex"


def test_md_escapes_pipes_so_the_table_survives():
    text = render.to_md([{"note": "a|b"}])
    assert "a\\|b" in text


@pytest.mark.parametrize("fn", [render.to_csv, render.to_jsonl])
def test_empty_rows_render_empty_not_crash(fn):
    assert fn([]) == ""


def test_empty_rows_are_reported_not_crashed():
    assert "no rows" in render.to_table([], "Results")
    assert render.to_md([]) == "_no rows_"


def test_non_ascii_survives_every_format():
    # Spec section 9: these sources return accented text constantly.
    rows = [{"pais": "Perú", "nota": "Côte d'Ivoire"}]
    for fn in (render.to_csv, render.to_jsonl, render.to_md, render.to_table):
        text = fn(rows) if fn is not render.to_table else fn(rows, "t")
        assert "Perú" in text or "Per\\u00fa" in text


def test_colored_respects_no_color(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert render.colored("x", "red") != "x"
    assert render.colored("x", "red", no_color=True) == "x"
    monkeypatch.setenv("NO_COLOR", "1")
    assert render.colored("x", "red") == "x"


def test_emit_writes_file_and_keeps_stdout_clean(tmp_path, capsys):
    target = tmp_path / "nested" / "out.csv"
    render.emit(render.envelope("list", ROWS), "csv", target)
    assert target.read_text(encoding="utf-8").startswith("tool,count,ok,extra")
    captured = capsys.readouterr()
    assert captured.out == ""  # the data went to the file, not stdout
    assert "Wrote 2 rows" in captured.err  # the note went to stderr


def test_fail_puts_parseable_envelope_on_stdout_in_json_mode(capsys):
    code = render.fail("run", "usage", "bad flag", "see --help", "json", render.EXIT_USAGE)
    assert code == render.EXIT_USAGE
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "usage"
    assert "bad flag" in captured.err


def test_fail_keeps_stdout_clean_in_table_mode(capsys):
    render.fail("run", "usage", "bad flag", "", "table", render.EXIT_USAGE)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "bad flag" in captured.err
