"use client";

import { useEffect, useRef, useState } from "react";


/* ------------------------------------------------------------------ reveal */

/**
 * Fades its children in once, when they first scroll into view.
 *
 * Uses IntersectionObserver rather than a scroll listener so it costs nothing
 * while idle, and unobserves after firing so an element never re-animates.
 */
export function Reveal({
  children,
  index = 0,
  className = "",
  as = "div",
}: {
  children: React.ReactNode;
  index?: number;
  className?: string;
  as?: "div" | "section" | "li" | "article";
}) {
  // A callback ref rather than useRef: the rendered tag varies, so a typed
  // RefObject would have to satisfy every element type at once. This also
  // fires when the node actually mounts, which is what the observer wants.
  const [node, setNode] = useState<HTMLElement | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!node) return;

    // Anything already on screen at mount should not wait for a scroll that
    // may never come — on a short viewport that would leave it invisible.
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.05 },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [node]);

  // Widening to ElementType stops TypeScript intersecting the props of every
  // tag in the union, which is what makes a shared ref unassignable.
  const Component = as as React.ElementType;

  return (
    <Component
      ref={setNode}
      className={`reveal ${className}`}
      data-visible={visible || undefined}
      style={{ "--index": index } as React.CSSProperties}
    >
      {children}
    </Component>
  );
}

/* -------------------------------------------------------------------- code */

/**
 * A command line with a copy button.
 *
 * Install instructions exist to be copied, so the copy affordance is the point
 * rather than decoration. `navigator.clipboard` is unavailable on insecure
 * origins, so the button degrades to selecting the text instead of failing.
 */
export function CodeLine({ children, label }: { children: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const codeRef = useRef<HTMLElement>(null);

  async function copy() {
    try {
      await navigator.clipboard.writeText(children);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      const node = codeRef.current;
      if (!node) return;
      const range = document.createRange();
      range.selectNodeContents(node);
      const selection = window.getSelection();
      selection?.removeAllRanges();
      selection?.addRange(range);
    }
  }

  return (
    <div className="group relative">
      {label ? <div className="eyebrow mb-2">{label}</div> : null}
      <div className="flex items-center gap-3 rounded-[var(--radius-control)] border border-[var(--line)] bg-[var(--surface-sunken)] px-4 py-3">
        <span aria-hidden className="select-none font-mono text-xs text-[var(--ink-faint)]">
          $
        </span>
        <code
          ref={codeRef}
          className="min-w-0 flex-1 overflow-x-auto whitespace-pre font-mono text-[0.8125rem] text-[var(--ink)]"
        >
          {children}
        </code>
        <button
          type="button"
          onClick={copy}
          aria-label={copied ? "Copied" : `Copy: ${children}`}
          className="shrink-0 rounded border border-[var(--line)] bg-[var(--surface)] px-2 py-1 font-mono text-[0.6875rem] text-[var(--ink-muted)] transition-colors hover:text-[var(--ink)] active:scale-[0.98]"
        >
          {copied ? "copied" : "copy"}
        </button>
      </div>
    </div>
  );
}

/**
 * A multi-line code block. Same copy affordance, no `$` prompt.
 */
export function CodeBlock({ children, label }: { children: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(children);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard blocked; the text is selectable anyway */
    }
  }

  return (
    <div className="relative">
      {label ? <div className="eyebrow mb-2">{label}</div> : null}
      <pre className="overflow-x-auto rounded-[var(--radius-control)] border border-[var(--line)] bg-[var(--surface-sunken)] p-4 font-mono text-[0.8125rem] leading-relaxed text-[var(--ink)]">
        <code>{children}</code>
      </pre>
      <button
        type="button"
        onClick={copy}
        aria-label={copied ? "Copied" : "Copy snippet"}
        className="absolute right-3 top-3 rounded border border-[var(--line)] bg-[var(--surface)] px-2 py-1 font-mono text-[0.6875rem] text-[var(--ink-muted)] transition-colors hover:text-[var(--ink)] active:scale-[0.98]"
        style={{ top: label ? "2rem" : "0.75rem" }}
      >
        {copied ? "copied" : "copy"}
      </button>
    </div>
  );
}

