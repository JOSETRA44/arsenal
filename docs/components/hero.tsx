import { CodeLine, Reveal } from "@/components/primitives";
import { servers, totalCommands } from "@/content/servers.generated";

/**
 * A single very slow, very faint radial drift behind the hero.
 *
 * Fixed and pointer-events-none so it never participates in scrolling or hit
 * testing, and it animates only `transform`. Under `prefers-reduced-motion` the
 * animation is dropped entirely — the blob stays, it simply stops moving.
 */
function AmbientDrift() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div
        className="absolute left-1/2 top-[-20%] h-[70vh] w-[70vh] -translate-x-1/2 rounded-full"
        style={{
          background:
            "radial-gradient(circle, var(--pale-blue-fg) 0%, transparent 65%)",
          opacity: 0.04,
          animation: "drift 34s ease-in-out infinite alternate",
        }}
      />
      <style>{`
        @keyframes drift {
          from { transform: translate(-50%, 0) scale(1); }
          to   { transform: translate(-42%, 4vh) scale(1.12); }
        }
        @media (prefers-reduced-motion: reduce) {
          [aria-hidden] > div { animation: none !important; }
        }
      `}</style>
    </div>
  );
}

function Figure({ value, label }: { value: string | number; label: string }) {
  return (
    <div>
      <div className="display text-3xl md:text-4xl">{value}</div>
      <div className="eyebrow mt-1.5">{label}</div>
    </div>
  );
}

export function Hero() {
  const keyless = servers.filter((server) => server.auth === "none").length;

  return (
    <div className="relative">
      <AmbientDrift />
      <div className="mx-auto max-w-6xl px-6 pb-20 pt-28 md:pb-28 md:pt-40">
        <Reveal className="max-w-3xl">
          <div className="eyebrow mb-6">Model Context Protocol</div>
          <h1 className="display text-[2.75rem] leading-[1.06] md:text-6xl">
            Real sources for
            <br />
            research agents.
          </h1>
          <p className="mt-7 max-w-xl text-base leading-relaxed text-[var(--ink-muted)]">
            {servers.length} MCP servers that let an AI agent pull data from named
            sources — scholarly databases, national statistics, government
            registries — instead of recalling something plausible. Each is a
            separate package. They share one command contract, so what you learn
            driving one applies to all of them.
          </p>
        </Reveal>

        <Reveal index={1} className="mt-9 flex flex-wrap items-center gap-3">
          <a
            href="#install"
            className="rounded-[var(--radius-control)] bg-[var(--control)] px-5 py-2.5 text-sm font-medium text-[var(--control-ink)] transition-colors hover:bg-[var(--control-hover)] active:scale-[0.98]"
          >
            Install a server
          </a>
          <a
            href="#servers"
            className="rounded-[var(--radius-control)] border border-[var(--line)] px-5 py-2.5 text-sm font-medium text-[var(--ink)] transition-colors hover:border-[var(--line-strong)]"
          >
            See what they cover
          </a>
        </Reveal>

        <Reveal index={2} className="mt-12 max-w-xl">
          <CodeLine label="Fastest path — no key, no clone">
            claude mcp add openalex -- uvx openalex-mcp
          </CodeLine>
        </Reveal>

        <Reveal index={3} className="mt-16 border-t border-[var(--line)] pt-10">
          <div className="grid grid-cols-3 gap-8 md:max-w-lg">
            <Figure value={servers.length} label="servers" />
            <Figure value={totalCommands} label="commands" />
            <Figure value={keyless} label="need no key" />
          </div>
        </Reveal>
      </div>
    </div>
  );
}
