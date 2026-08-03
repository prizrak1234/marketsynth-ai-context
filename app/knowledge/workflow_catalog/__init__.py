"""Read-only n8n workflow metadata catalog — KB-WPL-01.2."""

from app.knowledge.workflow_catalog.contracts import (
    DuplicateFamily,
    WorkflowCatalogBundle,
    WorkflowTemplateRecord,
)
from app.knowledge.workflow_catalog.parser import parse_workflow_file
from app.knowledge.workflow_catalog.queries import load_catalog

__all__ = [
    "DuplicateFamily",
    "WorkflowCatalogBundle",
    "WorkflowTemplateRecord",
    "load_catalog",
    "parse_workflow_file",
]
