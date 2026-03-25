"""Command-line interface for Scientia."""
from __future__ import annotations
import sys
from pathlib import Path

import click

from scientia.strategies import fetch_source
from scientia.extractor import extract_metadata
from scientia.metadata_enrich import enrich_metadata
from scientia.installer import install_skill, InstallError
from scientia.pipeline import build_skill_deep, BuildError
from scientia.registry import Registry
from scientia.clawhub_publish import (
    ClawhubPublishError,
    publish_from_registry_tool_name,
    publish_skill,
)


def get_default_db_path() -> Path:
    return Path.home() / ".scientia" / "registry.db"


@click.group()
def cli():
    """Scientia — generate and install verified ScienceClaw skills from any source."""


@cli.command()
@click.argument("source")
@click.option("--source-type", default="text", show_default=True,
              help="Source type: openapi, github, doi, pypi, webpage, cli, pdf, text")
@click.option("--skills-root", default=None, type=click.Path(),
              help="Root directory for installed skills")
@click.option("--db", default=None, type=click.Path(),
              help="Path to registry database")
@click.option("--deep", is_flag=True, default=False,
              help="Deep mode: analyze repo README, extract MethodSpec, write executable_script.py")
def add(source, source_type, skills_root, db, deep):
    """Fetch SOURCE, extract metadata, generate and install a verified skill."""
    source = (source or "").strip()
    skills_path = Path(skills_root) if skills_root else Path.home() / ".scientia" / "skills"
    db_path = Path(db) if db else get_default_db_path()

    if deep:
        click.echo(f"Fetching {source!r} (deep mode)…")
        registry = Registry(db_path)
        try:
            result = build_skill_deep(
                source,
                source_type=source_type if source_type != "text" else None,
                install_to=skills_path,
                registry=registry,
            )
        except BuildError as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        click.echo(
            f"Success: skill '{result['tool_name']}' installed with executable script "
            f"(retries={result.get('retry_count', 0)})"
        )
        return

    click.echo(f"Fetching {source!r} (type={source_type})…")
    content = fetch_source(source, source_type)

    click.echo("Extracting metadata…")
    meta = extract_metadata(content, source_type)
    meta = enrich_metadata(meta, source, source_type, content=content)

    click.echo(f"Installing skill '{meta.tool_name}'…")
    registry = Registry(db_path)
    try:
        result = install_skill(meta, skills_root=skills_path, registry=registry)
    except InstallError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Success: skill '{meta.tool_name}' verified and installed (retries={result.retry_count})")


@cli.command(name="list")
@click.option("--db", default=None, type=click.Path(), help="Path to registry database")
def list_skills(db):
    """List all installed skills in the registry."""
    db_path = Path(db) if db else get_default_db_path()
    registry = Registry(db_path)
    records = registry.list_all()

    if not records:
        click.echo("No skills installed yet.")
        return

    for rec in records:
        click.echo(f"{rec.tool_name:30s}  {rec.verification_status:10s}  {rec.source_type}")


@cli.command()
@click.argument("tool_name")
@click.option("--db", default=None, type=click.Path(), help="Path to registry database")
def info(tool_name, db):
    """Show details for an installed skill."""
    db_path = Path(db) if db else get_default_db_path()
    registry = Registry(db_path)
    record = registry.get_by_tool_name(tool_name)

    if record is None:
        click.echo(f"Error: no skill named '{tool_name}' found.", err=True)
        sys.exit(1)

    click.echo(f"Tool:    {record.tool_name}")
    click.echo(f"Source:  {record.source}")
    click.echo(f"Type:    {record.source_type}")
    click.echo(f"Status:  {record.verification_status}")
    click.echo(f"Retries: {record.retry_count}")
    click.echo(f"Dir:     {record.skill_dir}")
    if record.sample_output:
        click.echo(f"Sample:  {record.sample_output[:200]}")


@cli.command()
@click.option("--tag", default=None, help="Filter by tag")
@click.option("--min-score", default=None, type=int, help="Minimum quality score")
@click.option("--verified-only", is_flag=True, default=False, help="Only verified skills")
@click.option("--db", default=None, type=click.Path(), help="Path to registry database")
def search(tag, min_score, verified_only, db):
    """Search skills by tag, quality score, or verification status."""
    db_path = Path(db) if db else get_default_db_path()
    registry = Registry(db_path)
    records = registry.search(tag=tag, min_score=min_score, verified_only=verified_only)

    if not records:
        click.echo("No skills found.")
        return

    for rec in records:
        score_str = f"{rec.quality_score:3d}" if rec.quality_score is not None else "  -"
        tags_str = ",".join(rec.tags) if rec.tags else ""
        click.echo(f"{rec.tool_name:30s}  {rec.verification_status:10s}  score={score_str}  [{tags_str}]")


@cli.command("push-clawhub")
@click.argument("tool_name", required=False, default=None)
@click.option(
    "--skill-path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=None,
    help="Skill directory (must contain SKILL.md). Overrides TOOL_NAME/registry lookup.",
)
@click.option("--slug", default=None, help="ClawHub slug (default: folder name)")
@click.option("--name", "display_name", default=None, help="Display name on ClawHub")
@click.option("--version", default="1.0.0", show_default=True, help="Semver (required by ClawHub)")
@click.option("--changelog", default="", show_default=True)
@click.option("--tags", default="latest", show_default=True, help="Comma-separated tags")
@click.option("--fork-of", default=None, help="Parent skill slug[@version]")
@click.option("--db", default=None, type=click.Path(), help="Scientia registry DB")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print the clawhub command without running it",
)
def push_clawhub(
    tool_name,
    skill_path,
    slug,
    display_name,
    version,
    changelog,
    tags,
    fork_of,
    db,
    dry_run,
):
    """Publish an installed skill to ClawHub (requires: npm i -g clawhub ; clawhub login)."""
    db_path = Path(db) if db else get_default_db_path()

    if skill_path:
        skill_dir = Path(skill_path)
        try:
            code = publish_skill(
                skill_dir,
                slug=slug,
                display_name=display_name,
                version=version,
                changelog=changelog or None,
                tags=tags,
                fork_of=fork_of,
                dry_run=dry_run,
            )
        except ClawhubPublishError as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
    else:
        if not tool_name:
            click.echo("Error: pass TOOL_NAME or --skill-path", err=True)
            sys.exit(1)
        try:
            code = publish_from_registry_tool_name(
                tool_name,
                db_path,
                slug=slug,
                display_name=display_name,
                version=version,
                changelog=changelog or None,
                tags=tags,
                fork_of=fork_of,
                dry_run=dry_run,
            )
        except ClawhubPublishError as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

    if code != 0:
        sys.exit(code)


@cli.command("build-recipe")
@click.argument("recipe_file", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, type=click.Path(), help="Output script path")
def build_recipe(recipe_file, output):
    """Build a composite Python script from a skill recipe JSON file."""
    from scientia.recipe import parse_recipe_file, generate_script_to_file, RecipeError
    try:
        recipe = parse_recipe_file(Path(recipe_file))
    except RecipeError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    if output is None:
        output = f"{recipe.name}.py"

    out_path = Path(output)
    generate_script_to_file(recipe, out_path)
    click.echo(f"Built pipeline '{recipe.name}' → {out_path}")


if __name__ == "__main__":
    cli()
