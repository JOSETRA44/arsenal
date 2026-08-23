"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "arsenal-theme";

/**
 * Light/dark switch.
 *
 * The class on <html> is the source of truth: the inline script in layout.tsx
 * has already applied it before this component ever runs, so mounting reads
 * that class rather than re-deriving the preference and risking disagreement.
 *
 * Hydration: the server has no way to know the visitor's theme, so the first
 * client render must match the server's output exactly or React will warn and
 * discard the tree. Until `mounted` flips we render a placeholder of identical
 * size — same markup on both sides — and only then swap in the real state.
 */
export function ThemeToggle() {
  const [mounted, setMounted] = useState(false);
  const [dark, setDark] = useState(false);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
    setMounted(true);
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try {
      // Locked-down browsers throw on access rather than returning null, and a
      // failed write must not take the visual toggle down with it.
      localStorage.setItem(STORAGE_KEY, next ? "dark" : "light");
    } catch {
      /* preference is not persisted; the current page still switches */
    }
  }

  if (!mounted) {
    return (
      <span
        aria-hidden
        className="block h-9 w-9 rounded-[var(--radius-control)] border border-[var(--line)]"
      />
    );
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={dark}
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
      title={dark ? "Switch to light theme" : "Switch to dark theme"}
      className="flex h-9 w-9 items-center justify-center rounded-[var(--radius-control)] border border-[var(--line)] bg-[var(--surface)] text-[var(--ink-muted)] transition-colors hover:border-[var(--line-strong)] hover:text-[var(--ink)] active:scale-[0.98]"
    >
      {dark ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}

function SunIcon() {
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
      <circle cx="12" cy="12" r="4.25" />
      <path d="M12 2.5v2.2M12 19.3v2.2M21.5 12h-2.2M4.7 12H2.5M18.7 5.3l-1.6 1.6M6.9 17.1l-1.6 1.6M18.7 18.7l-1.6-1.6M6.9 6.9L5.3 5.3" />
    </svg>
  );
}

function MoonIcon() {
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
      strokeLinejoin="round"
    >
      <path d="M20 14.2A8.4 8.4 0 0 1 9.8 4a8.4 8.4 0 1 0 10.2 10.2Z" />
    </svg>
  );
}
