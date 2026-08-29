import { Contract } from "@/components/contract";
import { Hero } from "@/components/hero";
import { Install } from "@/components/install";
import { Reveal } from "@/components/primitives";
import { Section } from "@/components/ui";
import { ServerGrid } from "@/components/server-grid";
import { Verify } from "@/components/verify";
import { servers, totalCommands } from "@/content/servers.generated";

/**
 * The landing page.
 *
 * Order is an argument, not a layout: what this is (hero) → what you get
 * (servers) → how to get it (install) → why seven separate things behave like
 * one (contract). Someone who stops reading after the second section should
 * still have enough to install the one they need.
 */
export default function Home() {
  const keyless = servers.filter((server) => server.auth === "none").length;

  return (
    <>
      <Hero />

      <Section
        id="servers"
        eyebrow="The servers"
        title="Seven sources, one way to ask"
        lede={
          `Each one is an independent package you can install on its own. ` +
          `${keyless} of the ${servers.length} need no credentials at all — ` +
          `install and ask.`
        }
      >
        <ServerGrid />
      </Section>

      <Section
        id="install"
        eyebrow="Installation"
        title="Running in about a minute"
        lede="Pick a server, pick your client, paste. Nothing to clone and nothing to build."
      >
        <Install />
      </Section>

      <Verify />

      <Contract />

      <Section bordered>
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="display text-3xl md:text-4xl">Start with the keyless ones</h2>
          <p className="mx-auto mt-4 max-w-xl text-[0.9375rem] leading-relaxed text-[var(--ink-muted)]">
            OpenAlex covers most research questions and asks nothing of you. If it
            does not have your answer, one of the other {servers.length - 1} probably
            does — {totalCommands} commands between them.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <a
              href="#install"
              className="rounded-[var(--radius-control)] bg-[var(--control)] px-5 py-2.5 text-sm font-medium text-[var(--control-ink)] transition-colors hover:bg-[var(--control-hover)] active:scale-[0.98]"
            >
              Install a server
            </a>
            <a
              href="/servers/"
              className="rounded-[var(--radius-control)] border border-[var(--line)] px-5 py-2.5 text-sm font-medium text-[var(--ink)] transition-colors hover:border-[var(--line-strong)]"
            >
              Browse all {totalCommands} commands
            </a>
          </div>
        </Reveal>
      </Section>
    </>
  );
}
