"use client";

import { useId, useRef, useState } from "react";

import { CodeBlock, CodeLine } from "@/components/primitives";
import { servers, type Server } from "@/content/servers.generated";

type HostId = "claude-code" | "claude-desktop" | "vscode" | "generic";

const HOSTS: Array<{ id: HostId; label: string }> = [
  { id: "claude-code", label: "Claude Code" },
  { id: "claude-desktop", label: "Claude Desktop" },
  { id: "vscode", label: "VS Code / Cursor" },
  { id: "generic", label: "Any MCP client" },
];

const PREREQUISITES: Record<Server["ecosystem"], string> = {
  pypi: "Python 3.11 or newer, and uv (curl -LsSf https://astral.sh/uv/install.sh | sh)",
  npm: "Node 20 or newer",
  nuget: ".NET 10 SDK",
};

/**
 * The command each client needs, derived from the server's own install string.
 *
 * `install` is a full command line ("uvx openalex-mcp", "npx -y consultdn-mcp"),
 * so splitting it once here keeps every snippet consistent — a client config
 * needs the binary and its arguments as separate fields.
 */
function parts(server: Server): { command: string; args: string[] } {
  const [command, ...args] = server.install.split(" ");
  return { command, args };
}

function clientConfig(server: Server) {
  const { command, args } = parts(server);
  return { command, args };
}

function snippetFor(host: HostId, server: Server): { language: string; code: string } {
  const { command, args } = clientConfig(server);
  const entry = JSON.stringify({ command, args }, null, 2)
    .split("\n")
    .map((line, i) => (i === 0 ? line : "      " + line))
    .join("\n");

  switch (host) {
    case "claude-code":
      return { language: "bash", code: `claude mcp add ${server.slug} -- ${server.install}` };

    case "claude-desktop":
      return {
        language: "json",
        code: `{
  "mcpServers": {
    "${server.slug}": ${entry.trimStart()}
  }
}`,
      };

    case "vscode":
      return {
        language: "json",
        code: `{
  "servers": {
    "${server.slug}": {
      "type": "stdio",
      "command": ${JSON.stringify(command)},
      "args": ${JSON.stringify(args)}
    }
  }
}`,
      };

    default:
      return {
        language: "json",
        code: `{
  "command": ${JSON.stringify(command)},
  "args": ${JSON.stringify(args)}
}`,
      };
  }
}

function LocationNote({ host }: { host: HostId }) {
  if (host === "claude-desktop") {
    return (
      <p className="text-sm leading-relaxed text-[var(--ink-muted)]">
        Put this in <code className="font-mono text-xs">claude_desktop_config.json</code>, then
        restart Claude Desktop. On macOS it lives at{" "}
        <code className="font-mono text-xs">
          ~/Library/Application Support/Claude/
        </code>
        ; on Windows at <code className="font-mono text-xs">%APPDATA%\Claude\</code>.
      </p>
    );
  }
  if (host === "vscode") {
    return (
      <p className="text-sm leading-relaxed text-[var(--ink-muted)]">
        Put this in <code className="font-mono text-xs">.vscode/mcp.json</code> in your
        workspace. Cursor reads the same file.
      </p>
    );
  }
  if (host === "claude-code") {
    return (
      <p className="text-sm leading-relaxed text-[var(--ink-muted)]">
        One command, no file to edit. Run it in any project and the server is
        registered for that workspace.
      </p>
    );
  }
  return (
    <p className="text-sm leading-relaxed text-[var(--ink-muted)]">
      Any client that speaks stdio MCP takes this object — the shape varies
      slightly per client, but the command and args do not.
    </p>
  );
}

export function Install() {
  const [host, setHost] = useState<HostId>("claude-code");
  const [slug, setSlug] = useState(servers[0].slug);
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const baseId = useId();

  const server = servers.find((s) => s.slug === slug) ?? servers[0];
  const snippet = snippetFor(host, server);

  /** Arrow-key navigation, per the WAI-ARIA tabs pattern. */
  function onTabKeyDown(event: React.KeyboardEvent, index: number) {
    const delta = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (delta === 0) return;
    event.preventDefault();
    const next = (index + delta + HOSTS.length) % HOSTS.length;
    setHost(HOSTS[next].id);
    tabRefs.current[next]?.focus();
  }

  return (
    <div className="grid gap-10 lg:grid-cols-[16rem_1fr] lg:gap-14">
      {/* Server picker */}
      <div>
        <div className="eyebrow mb-3">1 — Pick a server</div>
        <ul className="space-y-1">
          {servers.map((entry) => {
            const active = entry.slug === server.slug;
            return (
              <li key={entry.slug}>
                <button
                  type="button"
                  onClick={() => setSlug(entry.slug)}
                  aria-pressed={active}
                  className={`flex w-full items-center justify-between rounded-[var(--radius-control)] border px-3 py-2 text-left text-sm transition-colors ${
                    active
                      ? "border-[var(--line-strong)] bg-[var(--surface)] text-[var(--ink)]"
                      : "border-transparent text-[var(--ink-muted)] hover:border-[var(--line)]"
                  }`}
                >
                  <span>{entry.name}</span>
                  {entry.auth === "required" ? (
                    <span className="font-mono text-[0.625rem] text-[var(--ink-faint)]">key</span>
                  ) : null}
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      {/* Instructions */}
      <div>
        <div className="eyebrow mb-3">2 — Pick your client</div>

        <div role="tablist" aria-label="MCP client" className="flex flex-wrap gap-1.5">
          {HOSTS.map((entry, index) => {
            const active = entry.id === host;
            return (
              <button
                key={entry.id}
                ref={(node) => {
                  tabRefs.current[index] = node;
                }}
                type="button"
                role="tab"
                id={`${baseId}-tab-${entry.id}`}
                aria-selected={active}
                aria-controls={`${baseId}-panel`}
                tabIndex={active ? 0 : -1}
                onClick={() => setHost(entry.id)}
                onKeyDown={(event) => onTabKeyDown(event, index)}
                className={`rounded-[var(--radius-control)] border px-3.5 py-1.5 text-sm transition-colors ${
                  active
                    ? "border-[var(--line-strong)] bg-[var(--surface)] text-[var(--ink)]"
                    : "border-[var(--line)] text-[var(--ink-muted)] hover:text-[var(--ink)]"
                }`}
              >
                {entry.label}
              </button>
            );
          })}
        </div>

        <div
          role="tabpanel"
          id={`${baseId}-panel`}
          aria-labelledby={`${baseId}-tab-${host}`}
          className="mt-6 space-y-5"
        >
          <div className="card p-4">
            <div className="eyebrow mb-1.5">Before you start</div>
            <p className="text-sm text-[var(--ink-muted)]">{PREREQUISITES[server.ecosystem]}</p>
            {server.auth === "required" ? (
              <p className="mt-2 text-sm text-[var(--ink-muted)]">
                {server.name} also needs an API key — see its page for where to get
                one and which variable to set.
              </p>
            ) : null}
          </div>

          <LocationNote host={host} />

          {snippet.language === "bash" ? (
            <CodeLine>{snippet.code}</CodeLine>
          ) : (
            <CodeBlock>{snippet.code}</CodeBlock>
          )}

          <p className="text-sm leading-relaxed text-[var(--ink-muted)]">
            Nothing to clone and nothing to build:{" "}
            <code className="font-mono text-xs">{parts(server).command}</code> fetches
            the package on first run and caches it.
          </p>
        </div>
      </div>
    </div>
  );
}
