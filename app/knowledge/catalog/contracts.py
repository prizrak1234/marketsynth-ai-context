"""Catalog search contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RecommendedAction = Literal[
    "use_internal_skill",
    "review_methodology",
    "adapt_workflow_pattern",
    "inspect_error_pattern",
    "request_security_review",
    "request_owner_review",
    "defer",
    "reject",
]


class CatalogSearchResult(BaseModel):
    artifact_id: str
    title: str
    artifact_type: str
    summary: str
    capabilities: list[str] = Field(default_factory=list)
    source: str
    trust_status: str
    adaptation_status: str
    security_findings: list[str] = Field(default_factory=list)
    matching_fields: list[str] = Field(default_factory=list)
    ranking_explanation: str
    related_artifacts: list[str] = Field(default_factory=list)
    recommended_action: RecommendedAction

    model_config = {"extra": "forbid"}
