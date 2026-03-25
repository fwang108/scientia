"""Subprocess-based verifier for generated skill scripts."""
from __future__ import annotations
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

from scientia.llm import llm_complete
from scientia.models import VerificationResult

if TYPE_CHECKING:
    from scientia.models import ToolMetadata


@dataclass
class VerifierConfig:
    timeout: int = 30
    max_retries: int = 3
    fix_callback: Optional[Callable[[str, VerificationResult], str]] = field(
        default=None, compare=False
    )


def make_llm_fix_callback(
    llm_fn: Optional[Callable[[str], str]] = None,
) -> Callable[[str, VerificationResult], str]:
    """Return a fix_callback that uses an LLM to repair a failing script.

    Args:
        llm_fn: callable(prompt) -> str.  Defaults to ``scientia.llm.llm_complete``.

    The returned callback embeds the original script and the error message into a
    prompt, calls the LLM, strips any markdown code fences from the response, and
    returns the repaired script string.
    """
    _llm = llm_fn if llm_fn is not None else llm_complete

    def _callback(script: str, result: VerificationResult) -> str:
        error = result.error_summary or result.stderr or result.stdout or "unknown error"
        prompt = (
            "You are a Python script repair tool. The script below failed with the error shown.\n"
            "Return ONLY the corrected Python script with no explanation and no markdown fences.\n\n"
            f"ERROR:\n{error}\n\n"
            f"SCRIPT:\n{script}\n"
        )
        raw = _llm(prompt)
        return _strip_fences(raw)

    return _callback


def _strip_fences(text: str) -> str:
    """Remove leading/trailing markdown code fences (```python ... ```)."""
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


_PLACEHOLDER = "scientia_verify_placeholder"


def _normalize_long_option_token(token: str) -> str:
    """Map ``--snake_case`` to ``--snake-case`` to match generated argparse flags.

    LLMs often echo parameter names with underscores; :func:`generate_client_script`
    registers ``--name-with-hyphens``.
    """
    if not token.startswith("--") or token.startswith("---"):
        return token
    if "=" in token:
        lhs, rhs = token.split("=", 1)
        if not lhs.startswith("--"):
            return token
        flag = "--" + lhs[2:].replace("_", "-")
        return f"{flag}={rhs}"
    return "--" + token[2:].replace("_", "-")


def _flags_present(argv: list[str]) -> set[str]:
    """Return long-option flags present in *argv* (--foo bar, --foo=bar)."""
    flags: set[str] = set()
    i = 0
    while i < len(argv):
        t = argv[i]
        if not t.startswith("--"):
            i += 1
            continue
        if "=" in t:
            flags.add(t.split("=", 1)[0])
            i += 1
            continue
        flags.add(t)
        if i + 1 < len(argv) and not argv[i + 1].startswith("-"):
            i += 2
        else:
            i += 1
    return flags


def build_verify_argv(meta: "ToolMetadata") -> list[str]:
    """Build argv so argparse sees every required flag (example_call + placeholders).

    Generated clients require explicit ``--name value`` pairs; the installer used
    to invoke the script with no args, so verification always failed whenever
    the LLM marked parameters as required.
    """
    raw = (meta.example_call or "").strip()
    tokens = shlex.split(raw, posix=True) if raw else []
    tokens = [_normalize_long_option_token(t) for t in tokens]
    # Strip leading command prefix (e.g. "python script.py" or "uv run train.py")
    # so only --flag value pairs are passed to the generated client script.
    first_flag = next((i for i, t in enumerate(tokens) if t.startswith("--")), len(tokens))
    tokens = tokens[first_flag:]
    flags = _flags_present(tokens)
    extra: list[str] = []
    for p in meta.all_parameters:
        if not p.required:
            continue
        flag = f"--{p.name.replace('_', '-')}"
        if flag in flags:
            continue
        extra.extend([flag, _PLACEHOLDER])
    return tokens + extra


def verify_script(
    script: str,
    work_dir: Path,
    config: Optional[VerifierConfig] = None,
    example_args: Optional[list[str]] = None,
) -> VerificationResult:
    """Run *script* in a subprocess and return a VerificationResult.

    If the run fails and *config.fix_callback* is set, it will be called
    with (script, result) and must return a revised script string.
    The revised script is then retried up to *config.max_retries* times.
    """
    if config is None:
        config = VerifierConfig()

    current_script = script
    retry_count = 0

    while True:
        result = _run_once(current_script, work_dir, config.timeout, example_args)

        if result.passed:
            return VerificationResult(
                passed=True,
                exit_code=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr,
                is_valid_json=result.is_valid_json,
                retry_count=retry_count,
                error_summary=None,
            )

        # Failed — no more retries possible
        if retry_count >= config.max_retries:
            return VerificationResult(
                passed=False,
                exit_code=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr,
                is_valid_json=result.is_valid_json,
                retry_count=retry_count,
                error_summary=result.stderr[:500] or result.stdout[:500],
            )

        retry_count += 1

        # Attempt fix if callback provided, otherwise retry same script
        if config.fix_callback is not None:
            current_script = config.fix_callback(current_script, result)


def _run_once(
    script: str,
    work_dir: Path,
    timeout: int,
    example_args: Optional[list[str]],
) -> VerificationResult:
    work_dir = Path(work_dir)
    fd, path_str = tempfile.mkstemp(
        suffix=".py", prefix="sci_verify_", dir=work_dir, text=True
    )
    script_path = Path(path_str)
    cmd = [sys.executable, str(script_path)]
    if example_args:
        cmd.extend(example_args)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(script)
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return VerificationResult(
                passed=False,
                exit_code=-1,
                stdout="",
                stderr="Timed out",
                is_valid_json=False,
                retry_count=0,
                error_summary="Script timed out",
            )

        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        exit_code = proc.returncode

        is_valid_json = False
        if stdout:
            try:
                json.loads(stdout)
                is_valid_json = True
            except json.JSONDecodeError:
                pass

        passed = exit_code == 0 and is_valid_json and bool(stdout)

        return VerificationResult(
            passed=passed,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            is_valid_json=is_valid_json,
            retry_count=0,
            error_summary=stderr[:500] if not passed else None,
        )
    finally:
        try:
            script_path.unlink(missing_ok=True)
        except OSError:
            pass
