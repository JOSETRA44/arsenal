import Link from "next/link";

import { Reveal } from "@/components/primitives";
import { ACCENT, Tag } from "@/components/ui";
import { servers, type Server } from "@/content/servers.generated";

/**
 * Auth is the one fact that changes what a reader does next: a keyless server
 * they can try in ten seconds, a keyed one is a detour through a signup form.
 * So it gets the accent colour and plain wording rather than a status dot.
 */
function authLabel(auth: Server["auth"]) {
  if (auth === "none") return { text: "no key", accent: "green" as const };
  if (auth === "optional") return { text: "key optional", accent: "blue" as const };
  return { text: "key required", accent: "red" as const };
}

/**
 * The two servers given extra space are chosen, not arbitrary: OpenAlex has the
 * widest reach and no key, so it is where most readers should start;
 * IAdetector is the one nothing else in the set does.
 */
const FEATURED = new Set(["openalex", "iadetector"]);

function ArrowIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M3 11L11 3M11 3H5M11 3V9" />
    </svg>
  );
}

function ServerCard({ server, index }: { server: Server; index: number }) {
  const auth = authLabel(server.auth);
  const featured = FEATURED.has(server.slug);

  return (
    <Reveal
      as="article"
      index={index}
      className={featured ? "md:col-span-2" : undefined}
    >
      <Link
        href={`/servers/${server.slug}/`}
        className="card card-interactive group flex h-full flex-col p-7 md:p-8"
      >
        <div className="mb-5 flex items-start justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <span
              aria-hidden
              className="h-2.5 w-2.5 rounded-full"
              style={{ background: ACCENT[server.accent].fg }}
            />
            <h3 className="display text-xl">{server.name}</h3>
          </div>
          <span className="text-[var(--ink-faint)] opacity-0 transition-opacity group-hover:opacity-100">
            <ArrowIcon />
          </span>
        </div>

        <p className="text-[0.9375rem] leading-relaxed text-[var(--ink)]">{server.tagline}</p>

        {featured ? (
          <p className="mt-3 text-sm leading-relaxed text-[var(--ink-muted)]">{server.blurb}</p>
        ) : null}

        <div className="mt-auto pt-6">
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <Tag accent={auth.accent}>{auth.text}</Tag>
            <Tag>{server.commandCount} commands</Tag>
          </div>
          <code className="block truncate font-mono text-xs text-[var(--ink-faint)]">
            {server.install}
          </code>
        </div>
      </Link>
    </Reveal>
  );
}

export function ServerGrid() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      {servers.map((server, index) => (
        <ServerCard key={server.slug} server={server} index={index} />
      ))}
    </div>
  );
}
