# arsenal

One entry point across every research CLI in this workspace — discover them,
search them, run them, and **grade them against [`ARSENAL-SPEC.md`](../ARSENAL-SPEC.md)**.

Seven tools currently answer research questions here: `openalex`, `scopus`,
`bcrp`, `inei`, `undata`, `consultdn`, `iadetector`. An agent handed a question
does not know which one answers it, and a maintainer changing one does not know
whether it still honours the contract. This closes both gaps.

Zero runtime dependencies, on purpose: the arsenal has to run from a bare
checkout in order to audit tools that are not installed yet.

## Install

```bash
uv tool install git+https://github.com/JOSETRA44/arsenal.git
```

Or run it straight from the checkout:

```bash
PYTHONPATH=src python -m arsenal list
```

## Commands

### `arsenal list` — what exists

```
$ arsenal list
tool        status     auth      runtime  tags                                    summary
----------  ---------  --------  -------  --------------------------------------  ---------------------------------
openalex    installed  optional  python   academic, bibliometrics, citations       250M+ scholarly works, authors...
scopus      installed  required  python   academic, bibliometrics, h-index         Elsevier Scopus: papers, abst...
bcrp        installed  none      python   economics, peru, time-series, macro      Peru central bank time series...
```

`status` is `installed` (on PATH), `source` (checkout only), or `missing`.

### `arsenal search <term>` — which command answers this?

The index aggregates every tool's `describe --json`, then searches tags,
summaries, command names **and row fields**. Row fields are the point: an agent
asks for `h_index` or `cited_by_count`, and only the manifest knows which
command produces that column.

```bash
arsenal search h_index -f json | jq '.rows[] | {tool, command, example}'
arsenal search "exchange rate"
arsenal search peru
```

### `arsenal doctor` — is the arsenal actually consistent?

Grades every tool against the spec and exits non-zero if any tool fails.

```bash
arsenal doctor                      # static checks: --help and describe --json
arsenal doctor --live               # also runs one real example per tool
arsenal doctor openalex scopus      # just these
arsenal doctor -f json -o audit.json
```

Two tiers:

| Tier | Cost | Checks |
|---|---|---|
| static (default) | none — no network, no keys | resolvable, `--help` exits 0, `describe --json` parses, manifest keys, all five formats, exit codes documented, commands well-formed, examples present |
| `--live` | network calls + API quota | the envelope is real and complete, `count == len(rows)`, and a repeated call is served from the disk cache |

`--prefer source` (the default) audits the working tree; `--prefer installed`
audits the copy on PATH. An installed console script is a snapshot from
whenever it was last installed, so it will not reflect uncommitted work.

Findings are graded `pass` / `warn` / `fail`. Only `fail` breaks compliance —
a tool with no external API genuinely has no auth or rate-limit exit path, so
an undocumented code 4 is a `warn`, not a defect.

### `arsenal install` / `arsenal test` / `arsenal verify` — the whole set at once

Seven projects across three ecosystems means seven install incantations and
seven test runners. These collapse that into one command each:

```bash
arsenal install                  # every CLI and MCP server onto PATH
arsenal install openalex bcrp    # or just these
arsenal test                     # every project's own suite, one table
arsenal verify                   # install, test, then audit — exits non-zero on any failure
arsenal verify --skip-install    # when everything is already installed
```

One project failing never stops the rest: each step is reported with its exit
code and the most useful line of its output, so six passing and one broken reads
as six passing and one broken.

### `arsenal doctor --mcp` — does a client actually reach it?

The checks above grade the **CLI**. That is the larger half of each project but
not the half an MCP client uses, and the two diverge: a server whose CLI is
flawless still fails to connect if its entry point dies on import, and all the
client reports is `connection closed`.

`--mcp` runs the real handshake over stdio — `initialize`, the
`notifications/initialized` acknowledgement, then `tools/list` — and reports
what the server said about itself:

```bash
arsenal doctor --mcp
arsenal doctor scopus --mcp --prefer installed
```

It distinguishes two failures that need very different fixes. A server that
exits with code 4 (the contract's auth code) is *fine* — the environment simply
has no API key, which is one line for the user to set, so that is a warning. A
server that crashes, hangs, or exits any other way is a defect, and the report
carries its exit code and its own stderr instead of a bare timeout.

### `arsenal run <tool> [args...]` — passthrough

```bash
arsenal run openalex search-works "graph neural networks" -f jsonl --all --max 500
arsenal run bcrp series PN01288PM --years 2015:2025 -f csv -o pbi.csv
```

Verbatim in both directions: stdout, stderr and the tool's own exit code pass
straight through, so wrapping never hides a failure.

### `arsenal describe --json` — the arsenal's own manifest

The arsenal obeys the contract it audits — same flags, same envelope, same exit
codes, and a manifest derived from its own parser. Auditing a spec you do not
follow yourself is how specs rot.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | ok |
| 1 | one or more tools are not spec-compliant |
| 2 | usage error |
| 3 | tool not installed |
| 4–6 | n/a — the arsenal makes no authenticated or network calls of its own |

## Adding a tool

Append one `Tool` entry to `src/arsenal/registry.py`. The registry is data, not
code: the index, the audit and the runner are all driven off that table, and
`test_registry_points_at_directories_that_exist` will catch a typo in the path.

Then make the tool itself satisfy `ARSENAL-SPEC.md`, and confirm it with
`arsenal doctor <name> --live`.

## Tests

```bash
uv run --no-project --with pytest python -m pytest -q
```

The suite is hermetic — it never invokes a real tool. Rendering, envelope
shape, manifest grading, example parsing and index search are all tested
against fixtures.
