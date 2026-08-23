import Link from "next/link";

import { servers, totalCommands } from "@/content/servers.generated";

const GITHUB = "https://github.com/JOSETRA44";
const REPO = `${GITHUB}/research-arsenal`;

const DOCS = [
  { href: REPO, label: "Repository" },
  { href: `${REPO}/blob/main/ARSENAL-SPEC.md`, label: "ARSENAL-SPEC.md" },
  { href: `${REPO}/blob/main/DOCS-STANDARD.md`, label: "DOCS-STANDARD.md" },
];

export function Footer() {
  // Counted from the generated content so the figures cannot drift from the
  // CLIs they describe.
  const serverCount = servers.length;
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-[var(--line)]">
      <div className="mx-auto max-w-6xl px-6 py-16 md:py-20">
        <div className="grid gap-12 md:grid-cols-4 md:gap-8">
          <div className="md:col-span-2 md:pr-12">
            <div className="text-[0.9375rem] tracking-[-0.01em] text-[var(--ink)]">
              Research <span className="display text-[1.15rem]">Arsenal</span>
            </div>
            <p className="mt-3 max-w-sm text-[0.8125rem] leading-relaxed text-[var(--ink-muted)]seed">
              {serverCount} command-line tools for research data — scholarly, statistical and
              civic — that speak the same CLI contract and double as MCP servers.
            </p>
            <p className="mt-4 font-mono text-[0.75rem] text-[var(--ink-faint)]">MIT licensed</p>
          </div>

          <div>
            <h2 className="eyebrow mb-4">Servers</h2>
            <ul className="space-y-2.5">
              {servers.map((server) => (
                <li key={server.slug}>
                  <Link
                    href={`/servers/${server.slug}/`}
                    className="text-[0.8125rem] text-[var(--ink-muted)] transition-colors hover:text-[var(--ink)]"
                  >
                    {server.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h2 className="eyebrow mb-4">Documentation</h2>
            <ul className="space-y-2.5">
              {DOCS.map((doc) => (
                <li key={doc.href}>
                  <a
                    href={doc.href}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="text-[0.8125rem] text-[var(--ink-muted)] transition-colors hover:text-[var(--ink)]"
                  >
                    {doc.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <div className="border-t border-[var(--line)]">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-6 py-6 font-mono text-[0.75rem] text-[var(--ink-faint)] sm:flex-row sm:items-center sm:justify-between">
          <span>
            {serverCount} servers &middot; {totalCommands} commands
          </span>
          <span>&copy; {year} JOSETRA44</span>
        </div>
      </div>
    </footer>
  );
}
