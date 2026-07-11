"""okf-bridge command-line interface.

Thin wrapper only: argument parsing and I/O. All logic lives in pure
functions (exporter.export, importer.import_bundle, linker.link) so it
stays unit-testable. See CLAUDE.md ground rule 7.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import click

from graphify_okf_bridge import __version__
from graphify_okf_bridge.exporter import export as export_graph
from graphify_okf_bridge.graphify_io.loader import load_graph, save_graph
from graphify_okf_bridge.importer import import_bundle
from graphify_okf_bridge.linker import link as link_graphs
from graphify_okf_bridge.okf.reader import read_bundle
from graphify_okf_bridge.okf.validator import validate as validate_bundle
from graphify_okf_bridge.okf.writer import write_bundle


@click.group()
@click.version_option(__version__)
def main() -> None:
    """Bridge between Graphify knowledge graphs and OKF bundles."""


@main.command()
@click.argument("bundle_dir", type=click.Path(exists=True, file_okay=False))
@click.option("--strict", is_flag=True, help="Promote warnings to errors.")
def validate(bundle_dir: str, strict: bool) -> None:
    """Check BUNDLE_DIR for OKF v0.1 conformance (spec section 9)."""
    bundle, diagnostics = read_bundle(Path(bundle_dir))
    report = validate_bundle(bundle, diagnostics)

    for issue in [*report.errors, *report.warnings]:
        click.echo(f"{issue.level.upper():7} {issue.path}: {issue.message}")

    click.echo(f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)")

    if not report.ok(strict=strict):
        raise click.exceptions.Exit(1)


@main.command()
@click.argument("graph_json", type=click.Path(exists=True, dir_okay=False))
@click.option("-o", "--out", "bundle_dir", required=True, type=click.Path(file_okay=False))
def export(graph_json: str, bundle_dir: str) -> None:
    """Export a graphify GRAPH_JSON to an OKF bundle."""
    graph = load_graph(graph_json)
    bundle = export_graph(graph)
    write_bundle(bundle, Path(bundle_dir))


@main.command(name="import")
@click.argument("bundle_dir", type=click.Path(exists=True, file_okay=False))
@click.option("-o", "--out", "graph_json", required=True, type=click.Path(dir_okay=False))
def import_(bundle_dir: str, graph_json: str) -> None:
    """Import an OKF BUNDLE_DIR into a mergeable graphify graph.json."""
    bundle, read_diagnostics = read_bundle(Path(bundle_dir))
    graph, import_diagnostics = import_bundle(bundle)

    for diagnostic in [*read_diagnostics, *import_diagnostics]:
        click.echo(f"{diagnostic.level.upper():7} {diagnostic.path}: {diagnostic.message}")

    save_graph(graph, graph_json)


@main.command()
@click.argument("graph_json", type=click.Path(exists=True, dir_okay=False))
@click.argument("bundle_dir", type=click.Path(exists=True, file_okay=False))
@click.option("-o", "--out", "out_json", required=True, type=click.Path(dir_okay=False))
@click.option(
    "--repo-root",
    "repo_root",
    default=".",
    type=click.Path(exists=True, file_okay=False),
    help="Code repo root to scan for source files graph.json has no nodes for (e.g. .sql).",
)
def link(graph_json: str, bundle_dir: str, out_json: str, repo_root: str) -> None:
    """Infer code-to-data edges between GRAPH_JSON and BUNDLE_DIR."""
    graph = load_graph(graph_json)
    bundle, read_diagnostics = read_bundle(Path(bundle_dir))
    result = link_graphs(graph, bundle, Path(repo_root))

    for diagnostic in [*read_diagnostics, *result.diagnostics]:
        click.echo(f"{diagnostic.level.upper():7} {diagnostic.path}: {diagnostic.message}")
    click.echo(f"{len(result.edges)} edge(s) inferred")

    merged = graph.model_copy(
        update={
            "nodes": [*graph.nodes, *result.synthetic_nodes],
            "links": [*graph.links, *result.edges],
        }
    )
    save_graph(merged, out_json)


def _skill_registration(skill_path: str) -> str:
    return (
        "\n# okf-bridge\n"
        f"- **okf-bridge** (`{skill_path}`) "
        "- bridge between Graphify knowledge graphs and OKF bundles: "
        "export/import/link/validate. Trigger: `/okf-bridge`\n"
        'When the user types `/okf-bridge`, invoke the Skill tool with `skill: "okf-bridge"` '
        "before doing anything else.\n"
    )


@main.command(name="install-skill")
@click.option(
    "--project",
    is_flag=True,
    help="Install into the current repo's .claude/ instead of the user's home directory.",
)
def install_skill(project: bool) -> None:
    """Install the okf-bridge skill for Claude Code (mirrors `graphify install`)."""
    skill_src = Path(__file__).parent / "skill" / "SKILL.md"
    claude_dir = Path(".claude") if project else Path.home() / ".claude"

    skill_dst = claude_dir / "skills" / "okf-bridge" / "SKILL.md"
    skill_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(skill_src, skill_dst)
    click.echo(f"  skill installed  ->  {skill_dst}")

    skill_path = (
        ".claude/skills/okf-bridge/SKILL.md" if project else "~/.claude/skills/okf-bridge/SKILL.md"
    )
    registration = _skill_registration(skill_path)
    claude_md = claude_dir / "CLAUDE.md"
    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        if "# okf-bridge" in content:
            click.echo("  CLAUDE.md        ->  already registered (no change)")
        else:
            claude_md.write_text(content.rstrip() + "\n" + registration, encoding="utf-8")
            click.echo(f"  CLAUDE.md        ->  skill registered in {claude_md}")
    else:
        claude_md.parent.mkdir(parents=True, exist_ok=True)
        claude_md.write_text(registration.lstrip(), encoding="utf-8")
        click.echo(f"  CLAUDE.md        ->  created at {claude_md}")


if __name__ == "__main__":
    main()
