import { CodeBlock, CodeLine, Reveal } from "@/components/primitives";
import { Section } from "@/components/ui";
import { servers, totalCommands } from "@/content/servers.generated";

/**
 * Real output from `arsenal verify`, trimmed to fit.
 *
 * Copied from an actual run rather than composed: a fabricated terminal
 * transcript on a page about verification would be self-defeating.
 */
const TRANSCRIPT = `$ arsenal verify

installing openalex...   installing scopus...   installing bcrp...
testing openalex...      testing scopus...      testing bcrp...
auditing openalex...     auditing scopus...     auditing bcrp...

tool        step     ok   exit_code  seconds  detail
----------  -------  ---  ---------  -------  --------------------------
openalex    install  yes          0      6.2
openalex    test     yes          0      2.1  234 passed in 0.75s
openalex    audit    yes          0        0  10/10 checks
...
consultdn   build    yes          0      4.0
iadetector  test     yes          0     14.3  Superado: 77, Con error: 0

All 7 servers install, test and audit clean.`;

function Step({
  index,
  command,
  title,
  children,
}: {
  index: number;
  command: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Reveal as="li" index={index} className="border-t border-[var(--line)] pt-6">
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-xs text-[var(--ink-faint)]">
          {String(index + 1).padStart(2, "0")}
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-medium text-[var(--ink)]">{title}</h3>
          <p className="mt-1.5 text-sm leading-relaxed text-[var(--ink-muted)]">{children}</p>
          <div className="mt-3">
            <CodeLine>{command}</CodeLine>
          </div>
        </div>
      </div>
    </Reveal>
  );
}

export function Verify() {
  return (
    <Section
      id="verify"
      eyebrow="One command"
      title="Install all seven, then prove they work"
      lede={
        `Seven projects across three ecosystems means seven install incantations and ` +
        `seven test runners. This collapses all of it into one command that installs, ` +
        `tests and audits every server — and exits non-zero if any of it fails.`
      }
    >
      <div className="grid gap-12 lg:grid-cols-2 lg:gap-16">
        <div>
          <Reveal>
            <CodeLine label="Everything, end to end">arsenal verify</CodeLine>
          </Reveal>

          <ul className="mt-10 space-y-6">
            <Step index={0} title="Install every server" command="arsenal install">
              Puts each CLI and each MCP server on your PATH — <code className="font-mono text-xs">uv</code>{" "}
              for the Python ones, <code className="font-mono text-xs">npm</code> for
              ConsultDN, <code className="font-mono text-xs">dotnet</code> for IAdetector.
              One project failing does not stop the rest.
            </Step>

            <Step index={1} title="Run every test suite" command="arsenal test">
              Each project&apos;s own tests, in its own runner, reported in one table.
            </Step>

            <Step index={2} title="Audit the contract" command="arsenal doctor --mcp">
              Checks each CLI against the shared contract, then speaks the{" "}
              <strong className="font-medium text-[var(--ink)]">actual MCP protocol</strong>{" "}
              to each server: <code className="font-mono text-xs">initialize</code>, then{" "}
              <code className="font-mono text-xs">tools/list</code>. That is the half a
              client uses, and a perfect CLI tells you nothing about it.
            </Step>
          </ul>

          <Reveal index={3} className="mt-8 card p-5">
            <div className="eyebrow mb-2">Why the protocol check earns its place</div>
            <p className="text-sm leading-relaxed text-[var(--ink-muted)]">
              A server whose CLI passes every check can still fail to start for a
              client, and all the client reports is{" "}
              <code className="font-mono text-xs">connection closed</code>. Running the
              real handshake turns that into an exit code and the server&apos;s own
              stderr — including telling &quot;you have not set an API key&quot; apart
              from &quot;this crashed&quot;, which need very different fixes.
            </p>
          </Reveal>
        </div>

        <div className="space-y-6">
          <Reveal index={1}>
            <CodeBlock label="A real run">{TRANSCRIPT}</CodeBlock>
          </Reveal>

          <Reveal index={2}>
            <div className="card p-5">
              <div className="eyebrow mb-3">Scoped to what you need</div>
              <div className="space-y-3">
                <CodeLine>arsenal install openalex bcrp</CodeLine>
                <CodeLine>arsenal test undata -f json</CodeLine>
                <CodeLine>arsenal verify --skip-install</CodeLine>
              </div>
              <p className="mt-4 text-sm leading-relaxed text-[var(--ink-muted)]">
                Every command speaks the same contract as the servers it drives:{" "}
                <code className="font-mono text-xs">-f json</code> for a machine, a
                non-zero exit when something is wrong. It drops straight into CI.
              </p>
            </div>
          </Reveal>

          <Reveal index={3}>
            <p className="text-sm leading-relaxed text-[var(--ink-muted)]">
              Across {servers.length} servers that is {totalCommands} CLI commands and
              47 MCP tools, verified in one pass.
            </p>
          </Reveal>
        </div>
      </div>
    </Section>
  );
}
