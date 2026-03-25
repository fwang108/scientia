"""
Scientia — generate verified ScienceClaw-compatible skills from any scientific source.

Public API:
    build_skill(source, install_to=None) -> dict
    SkillExpander          — ScienceClaw bridge (gap → new skill)
    ConstraintDetector     — detect source type from a string
"""

__all__ = ["build_skill", "SkillExpander", "ConstraintDetector"]


def __getattr__(name):
    if name == "build_skill":
        from scientia.pipeline import build_skill
        return build_skill
    if name == "SkillExpander":
        from scientia.bridge import SkillExpander
        return SkillExpander
    if name == "ConstraintDetector":
        from scientia.detector import detect_source_type
        return detect_source_type
    raise AttributeError(f"module 'scientia' has no attribute {name!r}")
