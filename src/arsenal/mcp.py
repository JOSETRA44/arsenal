"""A minimal MCP stdio client, used to prove a server actually speaks the protocol.

``arsenal doctor`` grades the CLI half of each project. That is most of the
surface, but it is not the half an MCP client uses — and the two can diverge
badly: a server whose CLI is perfect still fails to connect if its entry point
crashes on import, and the symptom a user sees is a bare "connection closed"
with no explanation.

This module performs the real handshake — ``initialize``, the
``notifications/initialized`` acknowledgement, then ``tools/list`` — over the
same stdio transport a client uses. No dependencies: framing MCP is a
length-prefixed-free, newline-delimited JSON-RPC exchange, and implementing it
here keeps the arsenal installable from a bare checkout.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Any

PROTOCOL_VERSION = "2024-11-05"

CLIENT_INFO = {"name": "arsenal-doctor", "version": "0.1.0"}


@dataclass
class Handshake:
    """What a server told us about itself, or why it could not."""

    ok: bool
    server_name: str | None = None
    server_version: str | None = None
    protocol_version: str | None = None
    capabilities: dict[str, Any] = field(default_factory=dict)
    tools: list[dict[str, Any]] = field(default_factory=list)
    instructions: str | None = None
    error: str | None = None
    stderr: str = ""
    exit_code: int | None = None
    """Set when the server process died instead of answering."""

    @property
    def needs_credentials(self) -> bool:
        """True when the server exited cleanly reporting an auth/config problem.

        ARSENAL-SPEC reserves exit code 4 for exactly this. Distinguishing it
        from a crash matters: "you have not set an API key" is the user's to
        fix in one line, while "the server died" is ours.
        """
        return self.exit_code == 4

    @property
    def tool_names(self) -> list[str]:
        return [t.get("name", "") for t in self.tools]


class ServerGone(Exception):
    """The server closed its stdout — it has exited, or is about to."""


#: Distinguishes "the stream ended" from "nothing arrived yet". Collapsing the
#: two costs the whole timeout on every crashed server, and loses the exit code
#: that says *why* it crashed.
_EOF = object()


def _read_line(stream, timeout: float):
    """Read one line, returning ``_EOF`` at end of stream and ``None`` on timeout.

    A server that hangs without writing is the failure mode worth catching —
    plain ``readline()`` would block this process forever, so the read happens
    on a worker thread that we abandon if it overruns.
    """
    result: list[Any] = []

    def _worker() -> None:
        line = stream.readline()
        # readline() returns an empty string only at EOF; a blank line still
        # carries its newline, so the two are distinguishable.
        result.append(_EOF if line == "" else line)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(timeout)
    return result[0] if result else None


class StdioSession:
    """One MCP server subprocess, spoken to over stdin/stdout."""

    def __init__(self, argv: list[str], *, cwd: str | None = None, env: dict[str, str] | None = None):
        self._argv = argv
        self._cwd = cwd
        self._env = {**os.environ, **(env or {})}
        # A server that inherits a TTY-less pipe still writes logs to stderr;
        # capturing it is what makes a crash explainable instead of silent.
        self._proc: subprocess.Popen | None = None
        self._id = 0

    def __enter__(self) -> "StdioSession":
        self._proc = subprocess.Popen(
            self._argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=self._cwd,
            env=self._env,
        )
        return self

    def __exit__(self, *_exc: object) -> None:
        proc = self._proc
        if proc is None:
            return
        try:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    def _send(self, payload: dict[str, Any]) -> None:
        assert self._proc and self._proc.stdin
        self._proc.stdin.write(json.dumps(payload) + "\n")
        self._proc.stdin.flush()

    def request(self, method: str, params: dict[str, Any] | None = None, *, timeout: float = 30) -> dict[str, Any]:
        """Send a JSON-RPC request and return its response object."""
        assert self._proc and self._proc.stdout
        self._id += 1
        request_id = self._id
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}})

        # Servers legitimately emit notifications and log lines between a
        # request and its response, so read until the matching id turns up
        # rather than assuming the next line is ours.
        deadline_reads = 40
        for _ in range(deadline_reads):
            line = _read_line(self._proc.stdout, timeout)
            if line is None:
                raise TimeoutError(f"no response to {method} within {timeout:g}s")
            if line is _EOF:
                raise ServerGone(f"server closed stdout while awaiting {method}")
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                # Not JSON: a server writing logs to stdout. That is itself a
                # defect, but keep reading so the real response is not missed.
                continue
            if message.get("id") == request_id:
                return message
        raise TimeoutError(f"no response to {method} after {deadline_reads} messages")

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def postmortem(self, limit: int = 600, wait: float = 0) -> tuple[int | None, str]:
        """If the process has exited, its status and what it said on stderr.

        Only safe to call once the process is known to be gone — reading a live
        server's stderr blocks until it decides to write something.
        """
        proc = self._proc
        if proc is None:
            return None, ""
        if wait:
            # After EOF the process is exiting but may not have been reaped yet.
            try:
                proc.wait(timeout=wait)
            except subprocess.TimeoutExpired:
                pass
        code = proc.poll()
        if code is None:
            return None, ""
        text = ""
        if proc.stderr is not None:
            try:
                text = proc.stderr.read() or ""
            except Exception:
                text = ""
        return code, " ".join(text.split())[:limit]


def handshake(argv: list[str], *, cwd: str | None = None, env: dict[str, str] | None = None,
              timeout: float = 45) -> Handshake:
    """Run the full client handshake against one server and report what happened."""
    try:
        with StdioSession(argv, cwd=cwd, env=env) as session:
            try:
                response = session.request(
                    "initialize",
                    {
                        "protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {},
                        "clientInfo": CLIENT_INFO,
                    },
                    timeout=timeout,
                )
            except (TimeoutError, ServerGone) as exc:
                # Silence usually means the process died before answering, and
                # its stderr says why — far more useful than "timed out".
                code, stderr_text = session.postmortem(wait=5)
                if code is not None:
                    return Handshake(
                        ok=False,
                        exit_code=code,
                        stderr=stderr_text,
                        error=f"server exited with code {code}"
                        + (f": {stderr_text}" if stderr_text else ""),
                    )
                return Handshake(ok=False, error=str(exc))

            if "error" in response:
                return Handshake(ok=False, error=f"initialize failed: {response['error']}")

            result = response.get("result") or {}
            info = result.get("serverInfo") or {}

            # A client must acknowledge before the server will serve requests.
            session.notify("notifications/initialized")

            tools: list[dict[str, Any]] = []
            tools_error: str | None = None
            try:
                listed = session.request("tools/list", timeout=timeout)
                if "error" in listed:
                    tools_error = f"tools/list failed: {listed['error']}"
                else:
                    tools = (listed.get("result") or {}).get("tools") or []
            except TimeoutError as exc:
                tools_error = str(exc)

            return Handshake(
                ok=tools_error is None,
                server_name=info.get("name"),
                server_version=info.get("version"),
                protocol_version=result.get("protocolVersion"),
                capabilities=result.get("capabilities") or {},
                tools=tools,
                instructions=result.get("instructions"),
                error=tools_error,
            )

    except FileNotFoundError as exc:
        return Handshake(ok=False, error=f"server executable not found: {exc}")
    except (TimeoutError, ServerGone) as exc:
        return Handshake(ok=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001 - the point is to report, not raise
        return Handshake(ok=False, error=f"{type(exc).__name__}: {exc}")
