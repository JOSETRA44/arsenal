"""Which research CLIs exist in this workspace, and how to invoke each one.

The registry is deliberately data, not code: adding a tool to the arsenal means
adding one ``Tool`` entry here. Everything else — the aggregated index, the
conformance audit, the passthrough runner — is driven off this table.

Invocation is a *list* of candidate argv prefixes tried in order. A tool that
has been installed onto PATH (``uv tool install``) is preferred because it is
by far the fastest; a source checkout is the fallback so the arsenal works in a
fresh clone where nothing has been installed yet.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

SPEC_FILE = "ARSENAL-SPEC.md"


def _find_workspace() -> tuple[Path, bool]:
    """Locate the directory holding the research projects.

    Walking up from ``__file__`` works from a source checkout but not once the
    arsenal is installed as a tool, where the package lives under the installer's
    own directory and the projects are nowhere above it. So: an explicit env var
    wins, then the nearest ancestor containing the spec, then the current
    directory's ancestors.

    Returns the path and whether it was actually *found* rather than guessed,
    so callers can say "set ARSENAL_WORKSPACE" instead of reporting every tool
    as missing and leaving the user to figure out why.
    """
    override = os.environ.get("ARSENAL_WORKSPACE")
    if override:
        return Path(override).expanduser().resolve(), True

    here = Path(__file__).resolve()
    cwd = Path.cwd().resolve()
    for candidate in (*here.parents, cwd, *cwd.parents):
        if (candidate / SPEC_FILE).is_file():
            return candidate, True

    return (here.parents[3] if len(here.parents) > 3 else cwd), False


WORKSPACE, WORKSPACE_FOUND = _find_workspace()

WORKSPACE_HINT = (
    "No " + SPEC_FILE + " was found above this package or the current directory, so the "
    "workspace is a guess (" + str(WORKSPACE) + "). Point at it explicitly with "
    "ARSENAL_WORKSPACE=/path/to/MCPs, or run from inside the workspace."
)


@dataclass(frozen=True)
class Tool:
    """One research CLI in the arsenal."""

    name: str
    """Short name used as the arsenal subcommand: ``arsenal run openalex ...``."""

    project_dir: str
    """Directory name under the workspace root."""

    script: str
    """Console-script name once installed on PATH."""

    summary: str
    """One line, shown by ``arsenal list``."""

    auth: str = "none"
    """``none`` | ``optional`` | ``required`` — whether an API key is needed."""

    env_keys: tuple[str, ...] = ()
    """Environment variables holding credentials, if any."""

    runtime: str = "python"
    """``python`` | ``node`` | ``dotnet`` — selects the source-checkout fallback."""

    tags: tuple[str, ...] = field(default_factory=tuple)
    """Free-form domain tags, searched by ``arsenal search``."""

    @property
    def path(self) -> Path:
        return WORKSPACE / self.project_dir

    def candidates(self, prefer: str = "installed") -> list[list[str]]:
        """Candidate argv prefixes, best first.

        ``prefer="source"`` flips the order so the working tree wins over an
        installed copy. That matters constantly during development: an
        installed console script is a snapshot from whenever it was last
        installed, so auditing it would grade yesterday's code.
        """
        installed: list[list[str]] = []
        source: list[list[str]] = []
        on_path = shutil.which(self.script)
        if on_path:
            installed.append([on_path])
        found = source  # everything appended below is a source-checkout route
        if not self.path.is_dir():
            return installed
        if self.runtime == "python":
            # `uv run --directory` resolves the project's own locked env, so a
            # source checkout works without polluting the ambient interpreter.
            found.append(["uv", "run", "--directory", str(self.path), self.script])
            # On Windows a running MCP server holds an open handle to the
            # project's console script, so the pre-run sync fails to replace it
            # (os error 32). `--no-sync` skips that rebuild; the script is only
            # a launcher, so it still imports the current source.
            found.append(
                ["uv", "run", "--directory", str(self.path), "--no-sync", self.script]
            )
        elif self.runtime == "node":
            for rel in ("dist/cli.js", "dist/index.js"):
                entry = self.path / rel
                if entry.is_file():
                    found.append(["node", str(entry)])
        elif self.runtime == "dotnet":
            for exe in self.path.glob("publish/**/" + self.script + ".exe"):
                found.append([str(exe)])
                break
            cli_project = self.path / "src" / "IAdetector.Cli"
            if cli_project.is_dir():
                found.append(["dotnet", "run", "--project", str(cli_project), "--"])
        return (source + installed) if prefer == "source" else (installed + source)


TOOLS: tuple[Tool, ...] = (
    Tool(
        name="openalex",
        project_dir="openalex-mcp",
        script="openalex",
        summary="250M+ scholarly works, authors, institutions, sources (OpenAlex).",
        auth="optional",
        env_keys=("OPENALEX_API_KEY", "OPENALEX_EMAIL"),
        tags=("academic", "bibliometrics", "citations", "open-access"),
    ),
    Tool(
        name="scopus",
        project_dir="scopus-mcp",
        script="scopus",
        summary="Elsevier Scopus: papers, abstracts, author h-index, citation timelines.",
        auth="required",
        env_keys=("SCOPUS_API_KEY", "SCOPUS_INST_TOKEN"),
        tags=("academic", "bibliometrics", "citations", "h-index"),
    ),
    Tool(
        name="bcrp",
        project_dir="BCRP-mcp",
        script="bcrp",
        summary="Peru central bank time series: FX, inflation, GDP, reserves, rates.",
        tags=("economics", "peru", "time-series", "macro"),
    ),
    Tool(
        name="inei",
        project_dir="INEI-mcp",
        script="inei",
        summary="Peru national statistics: census, indicators, ubigeo geography.",
        tags=("statistics", "peru", "census", "demography", "geography"),
    ),
    Tool(
        name="undata",
        project_dir="UNdata-mcp",
        script="undata",
        summary="UN Statistics SDMX: world development indicators, MDG, cross-country.",
        tags=("statistics", "global", "sdmx", "development", "time-series"),
    ),
    Tool(
        name="consultdn",
        project_dir="consultdn-mcp",
        script="consultdn",
        summary="Peru identity and company verification: DNI, RUC, exchange rate.",
        runtime="node",
        tags=("identity", "peru", "company", "verification", "osint"),
    ),
    Tool(
        name="iadetector",
        project_dir="IAdetector-mcp",
        script="iadetector",
        summary="Local AI-generated-text detection (ONNX ensemble, no external API).",
        runtime="dotnet",
        tags=("text-analysis", "integrity", "authorship", "local"),
    ),
)

BY_NAME: dict[str, Tool] = {t.name: t for t in TOOLS}
