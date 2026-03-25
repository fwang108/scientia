"""SkillRecipe model, parser, and composite script generator for Scientia."""
from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


class RecipeError(Exception):
    """Raised when a recipe definition is invalid."""


@dataclass
class SkillRecipe:
    """A named, ordered sequence of skill invocations."""

    name: str
    description: str
    steps: List[Dict[str, Any]]
    output: Optional[str] = None


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_recipe(data: Dict[str, Any]) -> SkillRecipe:
    """Parse a recipe from a plain dict.  Raises RecipeError on invalid input."""
    if "name" not in data:
        raise RecipeError("Recipe must have a 'name' field.")
    if "steps" not in data:
        raise RecipeError("Recipe must have a 'steps' field.")
    for i, step in enumerate(data["steps"]):
        if "skill" not in step:
            raise RecipeError(f"Step {i} is missing required 'skill' field.")
    return SkillRecipe(
        name=data["name"],
        description=data.get("description", ""),
        steps=data["steps"],
        output=data.get("output"),
    )


def parse_recipe_file(path: Path) -> SkillRecipe:
    """Load a recipe from a JSON file."""
    data = json.loads(Path(path).read_text())
    return parse_recipe(data)


# ---------------------------------------------------------------------------
# Script generation
# ---------------------------------------------------------------------------

def generate_script(recipe: SkillRecipe) -> str:
    """Generate a composite Python script that runs the recipe steps in order."""
    lines = [
        f'"""Auto-generated composite script for recipe: {recipe.name}',
        f"",
        f"{recipe.description}",
        f'"""',
        f"import json",
        f"import subprocess",
        f"import sys",
        f"",
        f"RECIPE_NAME = {recipe.name!r}",
        f"",
        f"",
        f"def run_step(skill_name, args=None):",
        f"    \"\"\"Run a single skill step and return its JSON output.\"\"\"",
        f"    cmd = [sys.executable, f\"skills/{{skill_name}}/scripts/{{skill_name}}.py\"]",
        f"    if args:",
        f"        for k, v in args.items():",
        f"            cmd += [f\"--{{k}}\", str(v)]",
        f"    result = subprocess.run(cmd, capture_output=True, text=True)",
        f"    if result.returncode != 0:",
        f"        raise RuntimeError(f\"Step {{skill_name}} failed: {{result.stderr}}\")",
        f"    return json.loads(result.stdout)",
        f"",
        f"",
        f"def main():",
        f"    results = {{}}",
    ]

    for step in recipe.steps:
        skill = step["skill"]
        args = step.get("args", {})
        lines.append(f"    results[{skill!r}] = run_step({skill!r}, {args!r})")

    if recipe.output:
        lines.append(f"    return results.get({recipe.output!r})")
    else:
        lines.append(f"    return results")

    lines += [
        f"",
        f"",
        f"if __name__ == \"__main__\":",
        f"    output = main()",
        f"    print(json.dumps(output, indent=2))",
    ]

    return "\n".join(lines) + "\n"


def generate_script_to_file(recipe: SkillRecipe, path: Path) -> None:
    """Write the generated composite script to *path*."""
    Path(path).write_text(generate_script(recipe))
