/**
 * Server-safe presentation pieces.
 *
 * These deliberately do NOT carry "use client". `ACCENT` is plain data, and a
 * value exported from a client module reaches a server component as a client
 * reference proxy rather than the object itself — indexing it then yields
 * undefined and the prerender dies. Data and pure markup belong on this side of
 * the boundary; only the pieces that need state or effects live in
 * primitives.tsx.
 */

import { Reveal } from "@/components/primitives";
import type { Accent } from "@/content/servers.generated";

/* ------------------------------------------------------------------ accents */

/**
 * The four spot pastels, as background/foreground pairs.
 *
 * Written as inline CSS variables rather than Tailwind classes because the
 * pairs are swapped wholesale in dark mode; a class-per-shade approach would
 * need eight classes and would still not track the token change.
 */
export const ACCENT: Record<Accent, { bg: string; fg: string }> = {
  red: { bg: "var(--pale-red-bg)", fg: "var(--pale-red-fg)" },
  blue: { bg: "var(--pale-blue-bg)", fg: "var(--pale-blue-fg)" },
  green: { bg: "var(--pale-green-bg)", fg: "var(--pale-green-fg)" },
  yellow: { bg: "var(--pale-yellow-bg)", fg: "var(--pale-yellow-fg)" },
};

/* --------------------------------------------------------------------- tag */

export function Tag({
  children,
  accent,
  title,
}: {
  children: React.ReactNode;
  accent?: Accent;
  title?: string;
}) {
  const style = accent
    ? { background: ACCENT[accent].bg, color: ACCENT[accent].fg }
    : { background: "var(--surface-sunken)", color: "var(--ink-muted)" };

  return (
    <span
      title={title}
      className="inline-flex items-center rounded-full px-2.5 py-0.5 text-[0.6875rem] font-medium uppercase tracking-[0.06em]"
      style={style}
    >
      {children}
    </span>
  );
}

/* ------------------------------------------------------------------ section */

export function Section({
  id,
  eyebrow,
  title,
  lede,
  children,
  bordered = true,
}: {
  id?: string;
  eyebrow?: string;
  title?: string;
  lede?: string;
  children: React.ReactNode;
  bordered?: boolean;
}) {
  return (
    <section id={id} className={bordered ? "border-t border-[var(--line)]" : undefined}>
      <div className="mx-auto max-w-6xl px-6 py-24 md:py-32">
        {eyebrow || title || lede ? (
          <Reveal className="mb-14 max-w-2xl">
            {eyebrow ? <div className="eyebrow mb-4">{eyebrow}</div> : null}
            {title ? <h2 className="display text-3xl md:text-4xl">{title}</h2> : null}
            {lede ? (
              <p className="mt-4 text-[0.9375rem] leading-relaxed text-[var(--ink-muted)]">
                {lede}
              </p>
            ) : null}
          </Reveal>
        ) : null}
        {children}
      </div>
    </section>
  );
}
