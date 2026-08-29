"""The MCP handshake and the install/test runners, exercised without real servers.

Every server here is a tiny Python script written to `tmp_path`, so the suite
stays hermetic and fast while still going through the genuine subprocess and
stdio path — a mocked transport would not have caught the EOF-versus-timeout
bug that made every crashed server take the full timeout to diagnose.
"""

from __future__ import annotations

import json
import sys
import textwrap

import pytest

from arsenal import lifecycle
from arsenal.mcp import Handshake, ServerGone, handshake


def write_server(tmp_path, body: str):
    """Write a fake stdio MCP server and return the argv that runs it."""
    script = tmp_path / "server.py"
    script.write_text(textwrap.dedent(body), encoding="utf-8")
    return [sys.executable, str(script)]


GOOD_SERVER = '''
    import json, sys

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        message = json.loads(line)
        if message.get("method") == "initialize":
            sys.stdout.write(json.dumps({
                "jsonrpc": "2.0", "id": message["id"],
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "fake", "version": "9.9"},
                },
            }) + "\\n")
            sys.stdout.flush()
        elif message.get("method") == "tools/list":
            sys.stdout.write(json.dumps({
                "jsonrpc": "2.0", "id": message["id"],
                "result": {"tools": [
                    {"name": "alpha", "description": "Does alpha things."},
                    {"name": "beta", "description": "Does beta things."},
                ]},
            }) + "\\n")
            sys.stdout.flush()
    '''


class TestHandshake:
    def test_a_healthy_server_reports_its_identity_and_tools(self, tmp_path):
        result = handshake(write_server(tmp_path, GOOD_SERVER), timeout=20)
        assert result.ok
        assert result.server_name == "fake"
        assert result.server_version == "9.9"
        assert result.tool_names == ["alpha", "beta"]

    def test_a_server_that_exits_reports_its_code_and_stderr(self, tmp_path):
        # The case that matters most in practice: a crash on import. Without the
        # exit code and stderr the user sees only "connection closed".
        argv = write_server(tmp_path, '''
            import sys
            print("Configuration error: no API key", file=sys.stderr)
            raise SystemExit(4)
        ''')
        result = handshake(argv, timeout=20)
        assert not result.ok
        assert result.exit_code == 4
        assert "no API key" in result.stderr

    def test_exit_code_four_is_reported_as_needing_credentials(self, tmp_path):
        # Exit 4 is the contract's auth code; the server is fine, the
        # environment is not, and those need different advice.
        argv = write_server(tmp_path, '''
            import sys
            print("Missing SCOPUS_API_KEY", file=sys.stderr)
            raise SystemExit(4)
        ''')
        assert handshake(argv, timeout=20).needs_credentials

    def test_any_other_exit_code_is_not_a_credentials_problem(self, tmp_path):
        argv = write_server(tmp_path, "raise SystemExit(1)")
        result = handshake(argv, timeout=20)
        assert not result.needs_credentials
        assert result.exit_code == 1

    def test_a_crashed_server_is_diagnosed_quickly_not_after_the_timeout(self, tmp_path):
        # Regression guard: EOF used to be indistinguishable from silence, so a
        # server that died instantly still cost the whole timeout to report.
        import time

        argv = write_server(tmp_path, "raise SystemExit(3)")
        started = time.monotonic()
        result = handshake(argv, timeout=30)
        assert not result.ok
        assert time.monotonic() - started < 15, "EOF should be detected without waiting out the timeout"

    def test_a_missing_executable_is_reported_rather_than_raised(self, tmp_path):
        result = handshake([str(tmp_path / "does-not-exist.exe")], timeout=10)
        assert not result.ok
        assert result.error

    def test_a_silent_server_times_out(self, tmp_path):
        # Holds stdin open and never answers — the genuine hang case.
        argv = write_server(tmp_path, '''
            import sys, time
            sys.stdin.readline()
            time.sleep(30)
        ''')
        result = handshake(argv, timeout=2)
        assert not result.ok
        assert "within" in (result.error or "")

    def test_log_lines_on_stdout_do_not_break_the_handshake(self, tmp_path):
        # Writing logs to stdout is a defect, but it should degrade rather than
        # make the server unreachable.
        argv = write_server(tmp_path, '''
            import json, sys
            print("starting up, not json")
            sys.stdout.flush()
            for line in sys.stdin:
                message = json.loads(line)
                if message.get("method") == "initialize":
                    print(json.dumps({"jsonrpc":"2.0","id":message["id"],"result":{
                        "protocolVersion":"2024-11-05","capabilities":{},
                        "serverInfo":{"name":"noisy","version":"1"}}}))
                    sys.stdout.flush()
                elif message.get("method") == "tools/list":
                    print(json.dumps({"jsonrpc":"2.0","id":message["id"],
                                      "result":{"tools":[]}}))
                    sys.stdout.flush()
        ''')
        result = handshake(argv, timeout=20)
        assert result.server_name == "noisy"

    def test_an_initialize_error_is_surfaced(self, tmp_path):
        argv = write_server(tmp_path, '''
            import json, sys
            for line in sys.stdin:
                message = json.loads(line)
                print(json.dumps({"jsonrpc":"2.0","id":message["id"],
                                  "error":{"code":-32603,"message":"boom"}}))
                sys.stdout.flush()
        ''')
        result = handshake(argv, timeout=20)
        assert not result.ok
        assert "boom" in (result.error or "")


class TestHandshakeShape:
    def test_tool_names_survives_a_tool_with_no_name(self):
        result = Handshake(ok=True, tools=[{"description": "x"}])
        assert result.tool_names == [""]

    def test_needs_credentials_is_false_when_the_server_never_exited(self):
        assert not Handshake(ok=True).needs_credentials


class TestLifecycle:
    def test_a_failing_step_is_reported_rather_than_raised(self, monkeypatch):
        from arsenal.registry import BY_NAME

        tool = BY_NAME["bcrp"]
        monkeypatch.setattr(type(tool), "test_command", lambda self: [sys.executable, "-c", "raise SystemExit(2)"])
        results = lifecycle.test_all([tool], timeout=60)
        assert len(results) == 1
        assert not results[0].ok
        assert results[0].exit_code == 2

    def test_a_missing_runner_is_reported_as_not_on_path(self, monkeypatch):
        from arsenal.registry import BY_NAME

        tool = BY_NAME["bcrp"]
        monkeypatch.setattr(type(tool), "test_command", lambda self: ["definitely-not-a-real-binary"])
        result = lifecycle.test_all([tool], timeout=30)[0]
        assert not result.ok
        assert result.exit_code == 127
        assert "PATH" in result.detail

    def test_a_successful_step_summarises_its_output(self, monkeypatch):
        from arsenal.registry import BY_NAME

        tool = BY_NAME["bcrp"]
        monkeypatch.setattr(
            type(tool), "test_command",
            lambda self: [sys.executable, "-c", "print('226 passed in 1.5s')"],
        )
        result = lifecycle.test_all([tool], timeout=60)[0]
        assert result.ok
        assert "226 passed" in result.detail

    def test_the_row_projection_is_json_shaped(self, monkeypatch):
        from arsenal.registry import BY_NAME

        tool = BY_NAME["bcrp"]
        monkeypatch.setattr(type(tool), "test_command", lambda self: [sys.executable, "-c", "pass"])
        row = lifecycle.test_all([tool], timeout=60)[0].row()
        json.dumps(row)
        assert set(row) == {"tool", "step", "ok", "exit_code", "seconds", "detail"}


class TestCommands:
    """Each runtime must map to a command that at least names the right runner."""

    @pytest.mark.parametrize(
        "name,runner",
        [("bcrp", "uv"), ("consultdn", "npm"), ("iadetector", "dotnet")],
    )
    def test_install_and_test_commands_match_the_runtime(self, name, runner):
        from arsenal.registry import BY_NAME

        tool = BY_NAME[name]
        assert tool.install_command()[0] == runner
        assert tool.test_command()[0] in (runner, "npx")

    def test_every_tool_declares_an_mcp_entry_point(self):
        from arsenal.registry import TOOLS

        missing = [t.name for t in TOOLS if not t.mcp_script and not t.mcp_source]
        assert missing == [], "no way to reach the MCP server for: " + str(missing)
