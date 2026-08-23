# Research Arsenal — landing page

The public site for the seven research MCP servers in this workspace: what they
are, what you can ask them, and how to install one.

Next.js 15 (App Router) + React 19 + Tailwind v4, built as a **static export**,
so it deploys to GitHub Pages or any static host with no server.

## Develop

```bash
npm install
npm run content   # regenerate the server catalogue from the real CLIs
npm run dev       # http://localhost:3000
```

## The content pipeline

Nothing about the servers is typed by hand. `scripts/generate-content.mjs` runs

```bash
arsenal index --refresh -f json
```

which asks every CLI to describe itself via `describe --json`, and writes
`content/servers.generated.ts`. That file is the single source of truth for the
site: names, versions, command lists, row fields, output formats, exit codes and
examples all come from the tools themselves.

The consequence worth knowing: **the site cannot advertise a command that does
not exist.** Add a command to a server, run `npm run content`, and it appears.
Rename one and the old name disappears. The generator refuses to write a partial
catalogue — if a server fails to describe itself, the build stops and names it.

Editorial copy that the manifests cannot know — taglines, the "what you can ask
it" phrasings, which accent a server carries — lives in the `EDITORIAL` map at
the top of the generator, keyed by slug.

Regenerate after any change to a server's CLI:

```bash
npm run content && npm run typecheck
```

## Structure

```
app/
  layout.tsx              Fonts, metadata, no-flash theme script, nav + footer
  page.tsx                The landing page: hero → servers → install → contract
  globals.css             Design tokens. Light and dark, one place.
  servers/page.tsx        Index of all seven
  servers/[slug]/page.tsx Per-server detail; statically generated per slug
  install/page.tsx        Standalone install guide
components/
  primitives.tsx          Tag, Reveal, CodeLine, CodeBlock, Section, ACCENT
  nav.tsx  theme-toggle.tsx  footer.tsx
  hero.tsx  server-grid.tsx  install.tsx  contract.tsx
content/
  servers.generated.ts    GENERATED — do not edit
scripts/
  generate-content.mjs    The generator
```

## Design

Premium utilitarian minimalism: warm monochrome, editorial serif headings
(Instrument Serif) against a geometric sans, and monospace for anything a reader
might copy. Colour is scarce and semantic — the four pale accents mark which
data source a card belongs to and whether it needs credentials.

Structure is carried by 1px hairlines rather than shadows. All of it is defined
once as CSS custom properties in `app/globals.css`; both themes redefine the
same token names, so no component branches on theme.

Dark mode is applied by a `dark` class on `<html>`, set **before first paint** by
an inline script in `layout.tsx`. A static export ships theme-less HTML, so
without that the page paints light and snaps to dark — worse than no toggle.

Motion is deliberately close to invisible: a 12px rise and a fade on scroll
entry, staggered across grids, driven by `IntersectionObserver` and animating
only `transform` and `opacity`. All of it collapses under
`prefers-reduced-motion`.

## Build and deploy

```bash
npm run build     # static HTML into out/
```

`out/` is self-contained. For GitHub Pages, publish that directory; the config
sets `trailingSlash` so directory-style URLs resolve without a rewrite rule.

## Accuracy

Two upstreams are degraded as of 2026-08-21 and the site says so on the affected
servers rather than quietly showing empty results: INEI's API returns HTTP 404 on
every path, and UNdata's `DF_UNDATA_WDI` dataflow returns HTTP 500. Those notices
are maintained by hand in the server detail page — re-check before a release.
