import { CodeBlock, Reveal } from "@/components/primitives";
import { Section } from "@/components/ui";
import { servers } from "@/content/servers.generated";

/**
 * Exit codes, taken from ARSENAL-SPEC.md section 2.
 *
 * Rendered from a literal rather than from `server.exitCodes` because each
 * server phrases its own table for its own domain; this section is about the
 * shared contract, so it states the shared meaning.
 */
const EXIT_CODES: Array<[string, string]> = [
  ["0", "Success — including an empty result set"],
  ["1", "The API returned an error or something unexpected"],
  ["2", "Usage error: bad flag, bad argument, unknown format"],
  ["3", "Resource not found"],
  ["4", "Auth or configuration error"],
  ["5", "Rate limited or quota exhausted"],
  ["6", "Network failure or timeout"],
];

const ENVELOPE = `{
  "ok": true,
  "command": "search-works",
  "source": "openalex",
  "fetched_at": "2026-08-22T14:03:11Z",
  "cached": false,
  "count": 10,
  "meta": { "page": 1, "per_page": 10, "total": 41233 },
  "data": { },
  "rows": [ ]
}`;

function Point({
  title,
  children,
  index,
}: {
  title: string;
  children: React.ReactNode;
  index: number;
}) {
  return (
    <Reveal as="li" index={index} className="border-t border-[var(--line)] pt-5">
      <h3 className="text-sm font-medium text-[var(--ink)]">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-[var(--ink-muted)]">{children}</p>
    </Reveal>
  );
}

export function Contract() {
  const formats = servers[0]?.formats ?? [];

  return (
    <Section
      id="contract"
      eyebrow="The shared contract"
      title="Why seven things behave like one"
      lede="Every server implements the same command contract. An agent that can drive one can drive all of them, and a script written against one keeps working against the next."
    >
      <div className="grid gap-12 lg:grid-cols-2 lg:gap-16">
        <div>
          <ul className="space-y-6">
            <Point title="One envelope" index={0}>
              Every command in <code className="font-mono text-xs">--format json</code>{" "}
              returns the same shape. <code className="font-mono text-xs">count</code>{" "}
              always equals the length of{" "}
              <code className="font-mono text-xs">rows</code>, and{" "}
              <code className="font-mono text-xs">rows</code> is the flat projection
              that also feeds CSV and Markdown — so switching format never changes
              the data, only its presentation.
            </Point>

            <Point title="Five formats" index={1}>
              {formats.map((format, i) => (
                <span key={format}>
                  <code className="font-mono text-xs">{format}</code>
                  {i < formats.length - 1 ? ", " : ""}
                </span>
              ))}
              . Data goes to stdout and notes to stderr, so piping to{" "}
              <code className="font-mono text-xs">jq</code> always yields something
              parseable.
            </Point>

            <Point title="Exit codes that mean something" index={2}>
              A script can branch on <em>why</em> a call failed rather than parsing
              an error string. An empty result is exit 0 — absence of data is an
              answer, not a failure.
            </Point>

            <Point title="A cache that survives the process" index={3}>
              A CLI exits after one call, so an in-memory cache would never be read.
              These write to disk, keyed on the request and never on your API key,
              and report <code className="font-mono text-xs">cached</code> in the
              envelope. Repeating a query costs nothing.
            </Point>

            <Point title="Self-describing" index={4}>
              <code className="font-mono text-xs">describe --json</code> returns a
              manifest of every command, argument and output field — derived from the
              parser itself, so it cannot drift from what the tool actually accepts.
              It is how an agent learns a server without reading its docs, and how
              this page was built.
            </Point>
          </ul>
        </div>

        <div className="space-y-8">
          <Reveal index={1}>
            <CodeBlock label="The envelope">{ENVELOPE}</CodeBlock>
          </Reveal>

          <Reveal index={2}>
            <div className="eyebrow mb-3">Exit codes</div>
            <div className="card overflow-hidden">
              <table className="w-full text-sm">
                <tbody>
                  {EXIT_CODES.map(([code, meaning], i) => (
                    <tr
                      key={code}
                      className={i > 0 ? "border-t border-[var(--line)]" : undefined}
                    >
                      <td className="w-14 px-4 py-2.5 align-top font-mono text-xs text-[var(--ink-faint)]">
                        {code}
                      </td>
                      <td className="px-4 py-2.5 text-[var(--ink-muted)]">{meaning}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Reveal>
        </div>
      </div>
    </Section>
  );
}
