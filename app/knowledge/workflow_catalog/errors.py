"""Workflow catalog errors."""

from __future__ import annotations


class WorkflowCatalogError(Exception):
    """Base workflow catalog error."""


class WorkflowParseError(WorkflowCatalogError):
    """Workflow JSON could not be parsed safely."""


class WorkflowValidationError(WorkflowCatalogError):
    """Catalog record failed schema validation."""
