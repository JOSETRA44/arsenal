"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ThemeToggle } from "@/components/theme-toggle";

const GITHUB = "https://github.com/JOSETRA44";

/** Absolute hashes so the links still resolve from a /servers/{slug}/ page. */
const LINKS = [
  { href: "/#servers", label: "Servers" },
  { href: "/#install", label: "Install" },
  { href: "/#contract", label: "Contract" },
];

export function Nav() {
  const [open, setOpen] = useState(false);

  // Escape closes the panel. Bound only while it is open so the page is not
  // paying for a key listener the rest of the time.
  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <header
      className="sticky top-0 z-40 border-b border-[var(--line)] backdrop-blur-md"
      style={{ background: "color-mix(in srgb, var(--canvas) 82%, transparent)" }}
    >
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-6">
        <Link
          href="/"
          className="shrink-0 text-[0.9375rem] tracking-[-0.01em] text-[var(--ink)]"
          onClick={() => setOpen(false)}
        >
          Research <span className="display text-[1.15rem]">Arsenal</span>
        </Link>

        <nav aria-label="Primary" className="ml-auto hidden items-center gap-7 md:flex">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-[0.8125rem] text-[var(--ink-muted)] transition-colors hover:text-[var(--ink)]"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2 md:ml-0">
          <a
            href={GITHUB}
            target="_blank"
            rel="noreferrer noopener"
            aria-label="Source on GitHub"
            title="Source on GitHub"
            className="hidden h-9 w-9 items-center justify-center rounded-[var(--radius-control)] border border-[var(--line)] bg-[var(--surface)] text-[var(--ink-muted)] transition-colors hover:border-[var(--line-strong)] hover:text-[var(--ink)] sm:flex"
          >
            <GitHubMark />
          </a>

          <ThemeToggle />

          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
            aria-controls="nav-panel"
            aria-label={open ? "Close menu" : "Open menu"}
            className="flex h-9 w-9 items-center justify-center rounded-[var(--radius-control)] border border-[var(--line)] bg-[var(--surface)] text-[var(--ink-muted)] transition-colors hover:border-[var(--line-strong)] hover:text-[var(--ink)] active:scale-[0.98] md:hidden"
          >
            {open ? <CloseIcon /> : <MenuIcon />}
          </button>
        </div>
      </div>

      {open ? (
        <div id="nav-panel" className="border-t border-[var(--line)] bg-[var(--canvas)] md:hidden">
          <nav aria-label="Primary, mobile" className="mx-auto max-w-6xl px-6 py-3">
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="block border-b border-[var(--line)] py-3 text-sm text-[var(--ink-muted)] transition-colors last:border-b-0 hover:text-[var(--ink)]"
              >
                {link.label}
              </Link>
            ))}
            <a
              href={GITHUB}
              target="_blank"
              rel="noreferrer noopener"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2 border-t border-[var(--line)] py-3 text-sm text-[var(--ink-muted)] transition-colors hover:text-[var(--ink)] sm:hidden"
            >
              <GitHubMark />
              GitHub
            </a>
          </nav>
        </div>
      ) : null}
    </header>
  );
}

/* ------------------------------------------------------------------- icons */

function MenuIcon() {
  return (
    <svg
      aria-hidden
      viewBox="0 0 24 24"
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
    >
      <path d="M4 7.5h16M4 16.5h16" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg
      aria-hidden
      viewBox="0 0 24 24"
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
    >
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}

/**
 * The GitHub mark, drawn as a fill rather than a stroke: the logo is only
 * recognisable in its solid form, and a traced outline reads as a smudge at
 * 16px. Every other icon on the site is a 1.75px stroke.
 */
function GitHubMark() {
  return (
    <svg aria-hidden viewBox="0 0 16 16" width="16" height="16" fill="currentColor">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.4 7.4 0 0 1 2-.27c.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
    </svg>
  );
}
