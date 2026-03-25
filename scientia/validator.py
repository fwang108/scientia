"""AST-based safety validator for generated skill scripts."""
from __future__ import annotations
import ast
import re
from dataclasses import dataclass, field
from typing import List


class ValidationError(Exception):
    """Raised when the script cannot be parsed."""


@dataclass
class ValidationResult:
    passed: bool
    violations: List[str] = field(default_factory=list)


# Patterns that look like hardcoded secrets in string literals
_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{16,}", re.IGNORECASE),          # OpenAI-style
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{20,}", re.IGNORECASE), # Bearer token
    re.compile(r"['\"][A-Za-z0-9_\-]{32,}['\"]"),                # Long opaque strings
]

# Variable names that suggest a secret is being hardcoded
_SECRET_VAR_RE = re.compile(
    r"(api[_\-]?key|secret|token|password|passwd|auth[_\-]?key)",
    re.IGNORECASE,
)


class _SafetyVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.violations: List[str] = []

    # ── dangerous calls ───────────────────────────────────────────────────────

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func

        # eval(...) / exec(...)
        if isinstance(func, ast.Name) and func.id in ("eval", "exec"):
            self.violations.append(f"Use of '{func.id}()' is forbidden (line {node.lineno})")

        # os.system(...) / os.popen(...)
        if isinstance(func, ast.Attribute) and func.attr in ("system", "popen"):
            if isinstance(func.value, ast.Name) and func.value.id == "os":
                self.violations.append(
                    f"Use of 'os.{func.attr}()' is forbidden (line {node.lineno})"
                )

        # subprocess.*(..., shell=True)
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            if func.value.id == "subprocess":
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        self.violations.append(
                            f"subprocess called with shell=True is forbidden (line {node.lineno})"
                        )

        # requests.get/post/put/patch/delete without timeout=
        if isinstance(func, ast.Attribute) and func.attr in (
            "get", "post", "put", "patch", "delete", "request"
        ):
            if isinstance(func.value, ast.Name) and func.value.id == "requests":
                has_timeout = any(kw.arg == "timeout" for kw in node.keywords)
                if not has_timeout:
                    self.violations.append(
                        f"requests.{func.attr}() called without timeout= (line {node.lineno})"
                    )

        self.generic_visit(node)

    # ── hardcoded secrets ─────────────────────────────────────────────────────

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name) and _SECRET_VAR_RE.search(target.id):
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    self.violations.append(
                        f"Possible hardcoded secret in variable '{target.id}' (line {node.lineno})"
                    )
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            for pat in _SECRET_PATTERNS:
                if pat.search(node.value):
                    self.violations.append(
                        f"Possible hardcoded secret string detected (line {node.lineno})"
                    )
                    break
        self.generic_visit(node)


def validate_script(source: str) -> ValidationResult:
    """Parse *source* and check for safety violations.

    Raises:
        ValidationError: if the source cannot be parsed as Python.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValidationError(f"Syntax error: {exc}") from exc

    visitor = _SafetyVisitor()
    visitor.visit(tree)

    return ValidationResult(
        passed=len(visitor.violations) == 0,
        violations=visitor.violations,
    )
