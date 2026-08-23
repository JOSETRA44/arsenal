import type { Metadata } from "next";
import { Instrument_Serif, JetBrains_Mono } from "next/font/google";

import { Footer } from "@/components/footer";
import { Nav } from "@/components/nav";
import { totalCommands, servers } from "@/content/servers.generated";

import "./globals.css";

const serif = Instrument_Serif({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-instrument-serif",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://josetra44.github.io/research-arsenal"),
  title: {
    default: "Research Arsenal — MCP servers for research",
    template: "%s — Research Arsenal",
  },
  description:
    `${servers.length} MCP servers for research and investigation, sharing one CLI contract: ` +
    `${totalCommands} commands, five output formats, one JSON envelope.`,
  keywords: [
    "MCP",
    "Model Context Protocol",
    "research",
    "OpenAlex",
    "Scopus",
    "BCRP",
    "INEI",
    "UNdata",
    "bibliometrics",
    "open data",
  ],
  openGraph: {
    type: "website",
    title: "Research Arsenal — MCP servers for research",
    description: `${servers.length} MCP servers sharing one CLI contract. ${totalCommands} commands.`,
  },
};

/**
 * Applies the stored theme before first paint.
 *
 * Next's static export ships HTML with no theme class, so without this the page
 * paints light and then snaps to dark — the flash is worse than no toggle at
 * all. Reading localStorage is wrapped because a locked-down browser throws on
 * access rather than returning null.
 */
const THEME_SCRIPT = `
(function () {
  try {
    var stored = localStorage.getItem("arsenal-theme");
    var prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (stored === "dark" || (stored !== "light" && prefersDark)) {
      document.documentElement.classList.add("dark");
    }
  } catch (e) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${serif.variable} ${mono.variable}`}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="min-h-dvh antialiased">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-[var(--control)] focus:px-4 focus:py-2 focus:text-[var(--control-ink)]"
        >
          Skip to content
        </a>
        <Nav />
        <main id="main">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
