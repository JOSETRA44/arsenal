import type { Metadata } from "next";
import Link from "next/link";

import { Reveal } from "@/components/primitives";
import { ACCENT, Tag } from "@/components/ui";
import { servers, totalCommands } from "@/content/servers.generated";

export const metadata: Metadata = {
  title: "All servers",
  description: `${servers.length} research MCP servers, ${totalCommands} commands.`,
};

const AUTH_LABEL = {
  none: { text: "no key", accent: "green" as const },
  optional: { text: "optional", accent: "blue" as const },
  required: { text: "key required", accent: "red" as const },
};

export default function ServersIndex() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-20 md:py-28">
      <Reveal>
        <div className="eyebrow mb-4">Catalogue</div>
        <h1 className="display text-4xl md:text-5xl">All servers</h1>
        <p className="mt-5 max-w-2xl text-[0.9375rem] leading-relaxed text-[var(--ink-muted)]">
          {servers.length} independent packages, {totalCommands} commands between them.
          Every row below is generated from the server&apos;s own manifest.
        </p>
      </Reveal>

      <Reveal index={1} className="mt-12">
        <ul className="card divide-y divide-[var(--line)] overflow-hidden">
          {servers.map((server) => {
            const auth = AUTH_LABEL[server.auth];
            return (
              <li key={server.slug}>
                <Link
                  href={`/servers/${server.slug}/`}
                  className="flex flex-col gap-3 p-5 transition-colors hover:bg-[var(--surface-sunken)] sm:flex-row sm:items-center sm:gap-6"
                >
                  <div className="flex min-w-0 flex-1 items-center gap-3">
                    <span
                      aria-hidden
                      className="h-2.5 w-2.5 shrink-0 rounded-full"
                      style={{ background: ACCENT[server.accent].fg }}
                    />
                    <div className="min-w-0">
                      <div className="font-medium text-[var(--ink)]">{server.name}</div>
                      <div className="truncate text-sm text-[var(--ink-muted)]">
                        {server.tagline}
                      </div>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Tag accent={auth.accent}>{auth.text}</Tag>
                    <Tag>{server.commandCount} cmds</Tag>
                  </div>
                  <code className="shrink-0 font-mono text-xs text-[var(--ink-faint)] sm:w-52 sm:text-right">
                    {server.install}
                  </code>
                </Link>
              </li>
            );
          })}
        </ul>
      </Reveal>
    </div>
  );
}
