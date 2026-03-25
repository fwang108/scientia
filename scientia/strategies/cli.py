"""Run a CLI command's --help and capture the output."""
from __future__ import annotations
import shlex
import subprocess
from scientia.strategies.base import StrategyError


def fetch_cli(command: str, timeout: int = 10) -> str:
    """Run *command* (or *command* --help) and return its stdout/stderr."""
    parts = shlex.split(command)
    # If the command doesn't already include a help flag, add --help
    if not any(p in ("--help", "-h", "--version", "-V") for p in parts):
        parts.append("--help")

    try:
        result = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (result.stdout + result.stderr).strip()
        if not output and result.returncode not in (0, 1):
            raise StrategyError(f"Command {command!r} produced no output (exit {result.returncode})")
        return output
    except FileNotFoundError as exc:
        raise StrategyError(f"Command not found: {command!r}") from exc
    except subprocess.TimeoutExpired as exc:
        raise StrategyError(f"Command {command!r} timed out") from exc
