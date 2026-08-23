import type { Metadata } from "next";

import { Install } from "@/components/install";
import { Reveal } from "@/components/primitives";
import { servers } from "@/content/servers.generated";

export const metadata: Metadata = {
  title: "Install",
  description: `Install any of the ${servers.length} research MCP servers in about a minute.`,
};

export default function InstallPage() {
  return (
    <div className="mx-auto max-w-6xl px-6 py-20 md:py-28">
      <Reveal className="mb-14 max-w-2xl">
        <div className="eyebrow mb-4">Installation</div>
        <h1 className="display text-4xl md:text-5xl">Running in about a minute</h1>
        <p className="mt-5 text-[0.9375rem] leading-relaxed text-[var(--ink-muted)]">
          Pick a server, pick your client, paste. Nothing to clone and nothing to
          build — the runner fetches the package on first use and caches it.
        </p>
      </Reveal>
      <Install />
    </div>
  );
}
