"""Core data models for Scientia."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Param:
    name: str
    type: str
    description: str
    required: bool
    default: Any

    def to_argparse_flag(self) -> dict:
        flag = {
            "name": f"--{self.name}",
            "type": self.type,
            "help": self.description,
            "required": self.required,
            "default": self.default,
        }
        return flag


@dataclass
class ToolMetadata:
    tool_name: str
    description: str
    base_url: Optional[str]
    auth_required: bool
    parameters: List[Param]
    example_call: str
    example_output_shape: str
    source_type: str
    #: Paper / dataset landing page (e.g. arXiv abs) — not a JSON HTTP API.
    reference_url: Optional[str] = None
    #: GitHub repo URL when skill was built from ``--source-type github`` (implementation source).
    repository_url: Optional[str] = None
    #: Markdown: prerequisites, install, run commands, data/API keys — so users can run the method.
    implementation_notes: Optional[str] = None
    #: How the skill is invoked: "api" (HTTP), "local" (subprocess), "library" (Python import).
    execution_mode: str = "api"

    @property
    def script_filename(self) -> str:
        return f"{self.tool_name}_client.py"

    @property
    def skill_dir_name(self) -> str:
        return self.tool_name.lower()

    @property
    def all_parameters(self) -> List[Param]:
        if not self.auth_required:
            return list(self.parameters)
        has_api_key = any(p.name == "api_key" for p in self.parameters)
        if has_api_key:
            return list(self.parameters)
        api_key_param = Param(
            name="api_key",
            type="str",
            description="API key for authentication",
            required=True,
            default=None,
        )
        return [api_key_param] + list(self.parameters)


@dataclass
class EnvSpec:
    """Environment requirements for running a method."""
    python_version: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    env_vars: Dict[str, str] = field(default_factory=dict)
    gpu_required: bool = False


@dataclass
class RepoInfo:
    """Information about a code repository."""
    url: str
    stars: int = 0
    language: Optional[str] = None
    description: Optional[str] = None


@dataclass
class MethodSpec:
    """Structured description of a computational method extracted from a paper."""
    name: str
    description: str
    input_spec: str
    output_spec: str
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    prerequisites: List[str] = field(default_factory=list)
    install_commands: List[str] = field(default_factory=list)
    run_commands: List[str] = field(default_factory=list)
    datasets: List[str] = field(default_factory=list)
    checkpoints: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    repository_url: Optional[str] = None
    env_spec: EnvSpec = field(default_factory=EnvSpec)


@dataclass
class VerificationResult:
    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    is_valid_json: bool
    retry_count: int
    error_summary: Optional[str]

    @property
    def output_preview(self) -> str:
        return self.stdout[:200]


@dataclass
class SkillRecord:
    skill_id: str
    tool_name: str
    source: str
    source_type: str
    skill_dir: str
    verification_status: str
    retry_count: int
    sample_output: Optional[str]
    generated_at: str
    last_verified_at: Optional[str]
    quality_score: Optional[int] = None
    tags: List[str] = field(default_factory=list)

    @property
    def is_verified(self) -> bool:
        return self.verification_status == "verified"
