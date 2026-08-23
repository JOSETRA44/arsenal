import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { CodeLine, Reveal } from "@/components/primitives";
import { ACCENT, Tag } from "@/components/ui";
import { servers, serverBySlug, type Server } from "@/content/servers.generated";

/**
 * Upstream outages, maintained by hand.
 *
 * These are facts about somebody else's server, so they cannot come from the
 * generated manifests. Re-check before a release: the quickest test is
 * `arsenal doctor <slug> --live`, which grades a well-formed error envelope as
 * a pass and reports the outage separately.
 */
const OUTAGES: Record<string, string> = {
  inei:
    "Checked 2026-08-21: the INEI API is returning HTTP 404 on every path, including its own root. " +
    "This server handles it correctly — you get exit code 3 and an error envelope explaining that the " +
    "source did not answer — but no live data can be retrieved until INEI restores it.",
  undata:
    "Checked 2026-08-21: the DF_UNDATA_WDI dataflow is returning HTTP 500 from data.un.org. " +
    "Other dataflows work. An empty result carries upstream_degraded so you can tell " +
    "\"there is no such data\" from \"the source did not answer\".",
};

/** Required by `output: "export"` — without it the build cannot emit these routes. */
export function generateStaticParams() {
  return servers.map((server) => ({ slug: server.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const server = serverBySlug(slug);
  if (!server) return {};
  return {
    title: server.name,
    description: `${server.tagline} ${server.commandCount} commands.`,
  };
}

function authLabel(auth: Server["auth"]) {
  if (auth === "none") return { text: "no key needed", accent: "green" as const };
  if (auth === "optional") return { text: "key optional", accent: "blue" as const };
  return { text: "key required", accent: "red" as const };
}

/**
 * Group commands by their leading token ("series get" → "series").
 *
 * Several servers namespace their commands, and a flat list of sixteen reads as
 * noise where four groups of four reads as a structure.
 */
function group(commands: Server["commands"]) {
  const groups = new Map<string, Server["commands"]>();
  for (const command of commands) {
    const [head, ...rest] = command.name.split(" ");
    const key = rest.length > 0 ? head : "";
    const bucket = groups.get(key) ?? [];
    bucket.push(command);
    groups.set(key, bucket);
  }
  return [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]));
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="eyebrow mb-1.5">{label}</div>
      <div className="text-sm text-[var(--ink)]">{value}</div>
    </div>
  );
}

export default async function ServerPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const server = serverBySlug(slug);
  if (!server) notFound();

  const auth = authLabel(server.auth);
  const outage = OUTAGES[server.slug];
  const grouped = group(server.commands);

  return (
    <div className="mx-auto max-w-5xl px-6 py-20 md:py-28">
      <Link
        href="/servers/"
        className="text-sm text-[var(--ink-muted)] transition-colors hover:text-[var(--ink)]"
      >
        ← All servers
      </Link>

      <Reveal className="mt-8">
        <div className="flex items-center gap-3">
          <span
            aria-hidden
            className="h-3 w-3 rounded-full"
            style={{ background: ACCENT[server.accent].fg }}
          />
          <h1 className="display text-4xl md:text-5xl">{server.name}</h1>
          <span className="font-mono text-xs text-[var(--ink-faint)]">v{server.version}</span>
        </div>
        <p className="mt-5 max-w-2xl text-base leading-relaxed text-[var(--ink)]">
          {server.tagline}
        </p>
        <p className="mt-3 max-w-2xl text-[0.9375rem] leading-relaxed text-[var(--ink-muted)]">
          {server.blurb}
        </p>
        <div className="mt-6 flex flex-wrap gap-2">
          <Tag accent={auth.accent}>{auth.text}</Tag>
          <Tag>{server.commandCount} commands</Tag>
          {server.tags.slice(0, 4).map((tag) => (
            <Tag key={tag}>{tag}</Tag>
          ))}
        </div>
      </Reveal>

      {outage ? (
        <Reveal index={1} className="mt-8">
          <div
            className="rounded-[var(--radius-card)] border p-5"
            style={{ borderColor: ACCENT.yellow.fg, background: ACCENT.yellow.bg }}
          >
            <div className="eyebrow mb-2" style={{ color: ACCENT.yellow.fg }}>
              Upstream status
            </div>
            <p className="text-sm leading-relaxed" style={{ color: ACCENT.yellow.fg }}>
              {outage}
            </p>
          </div>
        </Reveal>
      ) : null}

      <Reveal index={2} className="mt-14">
        <h2 className="display text-2xl">Install</h2>
        <div className="mt-5 space-y-4">
          <CodeLine label="Claude Code">{`claude mcp add ${server.slug} -- ${server.install}`}</CodeLine>
          <CodeLine label="Or run it directly">{server.install}</CodeLine>
        </div>
      </Reveal>

      <Reveal index={3} className="mt-14">
        <h2 className="display text-2xl">What you can ask it</h2>
        <ul className="mt-5 space-y-3">
          {server.asks.map((ask) => (
            <li
              key={ask}
              className="border-l-2 pl-4 text-[0.9375rem] leading-relaxed text-[var(--ink-muted)]"
              style={{ borderColor: ACCENT[server.accent].bg }}
            >
              {ask}
            </li>
          ))}
        </ul>
      </Reveal>

      <Reveal index={4} className="mt-14">
        <h2 className="display text-2xl">Details</h2>
        <div className="mt-5 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <Field label="Package" value={<code className="font-mono text-xs">{server.pkg}</code>} />
          <Field label="Registry" value={server.ecosystem} />
          {server.api ? <Field label="Upstream API" value={server.api} /> : null}
          {server.baseUrl ? (
            <Field
              label="Base URL"
              value={<code className="break-all font-mono text-xs">{server.baseUrl}</code>}
            />
          ) : null}
          <Field
            label="Output formats"
            value={<code className="font-mono text-xs">{server.formats.join(" · ")}</code>}
          />
        </div>
      </Reveal>

      <Reveal index={5} className="mt-14">
        <h2 className="display text-2xl">Commands</h2>
        <p className="mt-3 text-sm text-[var(--ink-muted)]">
          Every command, straight from the server&apos;s own{" "}
          <code className="font-mono text-xs">describe --json</code>.
        </p>

        <div className="mt-6 space-y-8">
          {grouped.map(([groupName, commands]) => (
            <div key={groupName || "_root"}>
              {groupName ? <div className="eyebrow mb-3">{groupName}</div> : null}
              <div className="card divide-y divide-[var(--line)] overflow-hidden">
                {commands.map((command) => (
                  <div key={command.name} className="p-5">
                    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                      <code className="font-mono text-sm text-[var(--ink)]">{command.name}</code>
                      {!command.network ? (
                        <span className="font-mono text-[0.625rem] text-[var(--ink-faint)]">
                          local
                        </span>
                      ) : null}
                    </div>
                    {command.summary ? (
                      <p className="mt-1.5 text-sm leading-relaxed text-[var(--ink-muted)]">
                        {command.summary}
                      </p>
                    ) : null}
                    {command.rowFields.length > 0 ? (
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {command.rowFields.map((field) => (
                          <code
                            key={field}
                            className="rounded bg-[var(--surface-sunken)] px-1.5 py-0.5 font-mono text-[0.6875rem] text-[var(--ink-faint)]"
                          >
                            {field}
                          </code>
                        ))}
                      </div>
                    ) : null}
                    {command.example ? (
                      <code className="mt-3 block overflow-x-auto whitespace-pre font-mono text-xs text-[var(--ink-faint)]">
                        {command.example}
                      </code>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Reveal>

      {Object.keys(server.exitCodes).length > 0 ? (
        <Reveal index={6} className="mt-14">
          <h2 className="display text-2xl">Exit codes</h2>
          <div className="card mt-5 overflow-hidden">
            <table className="w-full text-sm">
              <tbody>
                {Object.entries(server.exitCodes).map(([code, meaning], i) => (
                  <tr key={code} className={i > 0 ? "border-t border-[var(--line)]" : undefined}>
                    <td className="w-14 px-4 py-2.5 align-top font-mono text-xs text-[var(--ink-faint)]">
                      {code}
                    </td>
                    <td className="px-4 py-2.5 text-[var(--ink-muted)]">{meaning}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Reveal>
      ) : null}
    </div>
  );
}
