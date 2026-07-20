"""Decision Brief public API with dependency-safe lazy re-exports."""

from __future__ import annotations

from typing import Any

__all__ = [
    "DecisionBrief",
    "DecisionBriefService",
    "EvidenceGroup",
    "assemble_decision_brief_markdown",
    "build_decision_brief_prompt",
    "build_grouped_evidence_context",
    "build_topology_context",
    "render_decision_brief",
    "render_executive_dashboard",
    "render_topology_markdown",
    "resolve_topology_entity",
]


_RENDERER_EXPORTS = {
    "render_decision_brief",
    "render_topology_markdown",
}
_EXECUTIVE_EXPORTS = {"render_executive_dashboard"}


def __getattr__(name: str) -> Any:
    if name in _RENDERER_EXPORTS:
        from app.observatory.decision_brief import renderer

        return getattr(renderer, name)
    if name in _EXECUTIVE_EXPORTS:
        from app.observatory.decision_brief import executive_dashboard

        return getattr(executive_dashboard, name)
    if name in __all__:
        from app.observatory.decision_brief import service

        return getattr(service, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
