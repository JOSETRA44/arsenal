/**
 * Build the site's server catalogue from the arsenal's own manifests.
 *
 * Every command, format and example on this site comes from `arsenal index
 * --refresh`, which asks each CLI to describe itself. Hand-copying that list
 * would be wrong within a week; generating it means the page cannot claim a
 * command that does not exist.
 *
 * Run:  npm run content
 */

import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ARSENAL = resolve(HERE, "..", "..");
const WORKSPACE = resolve(ARSENAL, "..");
const OUT = resolve(HERE, "..", "content", "servers.generated.ts");

/** Editorial copy the manifests cannot know: why a reader should care. */
const EDITORIAL = {
  openalex: {
    slug: "openalex",
    name: "OpenAlex",
    pkg: "openalex-mcp",
    ecosystem: "pypi",
    install: "uvx openalex-mcp",
    tagline: "250M+ scholarly works, open and keyless.",
    blurb:
      "The widest free net to cast first. Works, authors, institutions and journals, with citation counts and h-indexes, and no API key between you and the data.",
    accent: "blue",
    asks: [
      "Find recent papers on graph neural networks, most cited first",
      "What is this researcher's h-index?",
      "Which institutions publish the most on CRISPR?",
    ],
  },
  scopus: {
    slug: "scopus",
    name: "Scopus",
    pkg: "scopus-mcp",
    ecosystem: "pypi",
    install: "uvx scopus-mcp",
    tagline: "Curated Elsevier metadata and citation timelines.",
    blurb:
      "Where OpenAlex stops. Author profiles, year-by-year citation histories and affiliation records, curated by Elsevier. Needs a free API key; some tools also need an institutional token.",
    accent: "red",
    asks: [
      "Give me the full abstract and keywords for this DOI",
      "Show this paper's citations year by year",
      "Find papers on machine learning in medicine since 2020",
    ],
  },
  bcrp: {
    slug: "bcrp",
    name: "BCRP",
    pkg: "bcrp-mcp",
    ecosystem: "pypi",
    install: "uvx bcrp-mcp",
    tagline: "Peru's central bank, updated daily.",
    blurb:
      "Exchange rates, inflation, GDP, reserves and interest rates straight from BCRPData. Fully public — no key, no registration. A built-in catalogue turns a keyword into a series code.",
    accent: "green",
    asks: [
      "How much is the dollar in Peru today?",
      "Plot Peru's GDP over the last ten years",
      "Export FX, inflation and GDP together as one CSV",
    ],
  },
  inei: {
    slug: "inei",
    name: "INEI",
    pkg: "inei-mcp",
    ecosystem: "pypi",
    install: "uvx inei-mcp",
    tagline: "Peru's census, indicators and ubigeo codes.",
    blurb:
      "Census profiles and statistical indicators, plus ubigeo — the geographic key nearly every other Peruvian dataset joins on. Leading zeros preserved, because 01 is not 1.",
    accent: "yellow",
    asks: [
      "List Peru's departments with their codes",
      "What's the census profile for this region?",
      "Find indicators about literacy",
    ],
  },
  undata: {
    slug: "undata",
    name: "UNdata",
    pkg: "undata-mcp",
    ecosystem: "pypi",
    install: "uvx undata-mcp",
    tagline: "UN Statistics over SDMX, cross-country.",
    blurb:
      "World development indicators and MDG series when the question spans more than one country. The reference implementation of the shared contract, and the only one that also writes Parquet.",
    accent: "blue",
    asks: [
      "Compare GDP per capita across Peru, Colombia and Brazil",
      "Show progress on the Millennium Development Goals",
      "Which indicators exist about poverty?",
    ],
  },
  consultdn: {
    slug: "consultdn",
    name: "ConsultDN",
    pkg: "consultdn-mcp",
    ecosystem: "npm",
    install: "npx -y consultdn-mcp",
    tagline: "Peruvian identity and company verification.",
    blurb:
      "DNI and RUC lookups against public government registries, plus the official SUNAT exchange rate. Built for batches: hundreds of identifiers, bounded concurrency, one bad row never aborts the run.",
    accent: "green",
    asks: [
      "Who does this DNI belong to?",
      "Give me this company's details by RUC",
      "Verify these 300 identifiers from a list",
    ],
  },
  iadetector: {
    slug: "iadetector",
    name: "IAdetector",
    pkg: "IAdetector.Cli",
    ecosystem: "nuget",
    install: "dnx IAdetector.Cli",
    tagline: "AI-text detection that never leaves your machine.",
    blurb:
      "Seven statistical signals plus two local ONNX models. No external API, no key, and the analysed text is never transmitted — so you can screen an unpublished manuscript without handing it to anyone.",
    accent: "red",
    asks: [
      "Was this text written by an AI?",
      "Screen these 500 documents",
      "Why did it reach that verdict?",
    ],
  },
};

function readIndex() {
  const raw = execFileSync(
    "uv",
    ["run", "--no-project", "python", "-m", "arsenal", "index", "--refresh", "-f", "json"],
    {
      cwd: ARSENAL,
      encoding: "utf8",
      maxBuffer: 32 * 1024 * 1024,
      env: { ...process.env, PYTHONPATH: "src", ARSENAL_WORKSPACE: WORKSPACE, NO_COLOR: "1" },
    },
  );
  return JSON.parse(raw).data.tools;
}

/** Keep only what the page renders — the raw manifests are far larger. */
function shape(entry) {
  const editorial = EDITORIAL[entry.tool];
  if (!editorial) return null;
  const manifest = entry.manifest ?? {};
  const commands = (manifest.commands ?? [])
    .filter((c) => c && c.name)
    .map((c) => ({
      name: c.name,
      summary: (c.summary ?? "").replace(/\s+/g, " ").trim(),
      rowFields: c.row_fields ?? [],
      example: (c.examples ?? [])[0] ?? null,
      network: c.network !== false,
    }));

  return {
    ...editorial,
    version: manifest.version ?? "0.0.0",
    auth: entry.auth ?? "none",
    tags: entry.tags ?? [],
    formats: manifest.formats ?? [],
    api: manifest.source?.api ?? null,
    baseUrl: manifest.source?.base_url ?? null,
    exitCodes: manifest.exit_codes ?? {},
    commandCount: commands.length,
    commands,
  };
}

const ORDER = ["openalex", "scopus", "bcrp", "inei", "undata", "consultdn", "iadetector"];

const servers = readIndex()
  .map(shape)
  .filter(Boolean)
  .sort((a, b) => ORDER.indexOf(a.slug) - ORDER.indexOf(b.slug));

if (servers.length !== ORDER.length) {
  const found = servers.map((s) => s.slug);
  const missing = ORDER.filter((s) => !found.includes(s));
  throw new Error(
    `Only ${servers.length}/${ORDER.length} servers described. Missing: ${missing.join(", ")}. ` +
      "Run `arsenal doctor --prefer source` to see which one failed to describe itself.",
  );
}

const banner = `// GENERATED by scripts/generate-content.mjs — do not edit by hand.
// Source: \`arsenal index --refresh\`, i.e. each CLI's own \`describe --json\`.
// Regenerate with: npm run content
`;

const body = `${banner}
export type Accent = "blue" | "red" | "green" | "yellow";

export interface Command {
  name: string;
  summary: string;
  rowFields: string[];
  example: string | null;
  network: boolean;
}

export interface Server {
  slug: string;
  name: string;
  pkg: string;
  ecosystem: "pypi" | "npm" | "nuget";
  install: string;
  tagline: string;
  blurb: string;
  accent: Accent;
  asks: string[];
  version: string;
  auth: "none" | "optional" | "required";
  tags: string[];
  formats: string[];
  api: string | null;
  baseUrl: string | null;
  exitCodes: Record<string, string>;
  commandCount: number;
  commands: Command[];
}

export const servers: Server[] = ${JSON.stringify(servers, null, 2)};

export const totalCommands = servers.reduce((n, s) => n + s.commandCount, 0);

export function serverBySlug(slug: string): Server | undefined {
  return servers.find((s) => s.slug === slug);
}
`;

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, body, "utf8");

const total = servers.reduce((n, s) => n + s.commandCount, 0);
console.log(`wrote ${OUT}`);
console.log(`${servers.length} servers, ${total} commands`);
