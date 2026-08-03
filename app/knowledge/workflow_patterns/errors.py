"""Workflow pattern extraction errors."""

from __future__ import annotations


class WorkflowPatternError(Exception):
    """Base workflow pattern error."""


class PatternValidationError(WorkflowPatternError):
    """Pattern failed validation."""


class SourceSupportError(WorkflowPatternError):
    """Pattern source support gate failed."""
