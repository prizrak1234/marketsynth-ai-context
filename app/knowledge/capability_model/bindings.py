"""Binding validation helpers."""

from __future__ import annotations

from typing import Any

from app.knowledge.capability_model.catalog import resolve_skill_exists
from app.knowledge.capability_model.contracts import CONNECTOR_CLASSES, TOOL_CLASSES
from app.knowledge.n8n_engineering.constants import KNOWN_PATTERN_IDS


def validate_capability_skill_binding(binding: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    skill_id = binding.get("skill_id")
    status = binding.get("status")
    if not binding.get("capability_id"):
        errors.append("missing_capability_id")
    if not skill_id:
        errors.append("missing_skill_id")
    elif status not in {"deferred", "future", "specified"} and not resolve_skill_exists(skill_id):
        errors.append(f"unknown_skill:{skill_id}")
    if binding.get("grants_permission"):
        errors.append("binding_grants_permission")
    if binding.get("activates_skill"):
        errors.append("binding_activates_skill")
    return errors


def validate_skill_pattern_binding(binding: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    pattern_id = binding.get("pattern_id")
    if pattern_id not in KNOWN_PATTERN_IDS:
        errors.append(f"unknown_pattern:{pattern_id}")
    if binding.get("grants_tool_permission"):
        errors.append("pattern_grants_tool_permission")
    if binding.get("runtime_authorized") is True:
        errors.append("pattern_runtime_authorized")
    return errors


def validate_pattern_connector_binding(binding: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    connector_class = binding.get("connector_class")
    if connector_class not in CONNECTOR_CLASSES:
        errors.append(f"unknown_connector_class:{connector_class}")
    if binding.get("activates_connector"):
        errors.append("connector_binding_activates")
    if binding.get("permission_granted"):
        errors.append("connector_permission_granted")
    return errors


def validate_connector_tool_binding(binding: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    tool_class = binding.get("tool_class")
    if tool_class not in TOOL_CLASSES:
        errors.append(f"unknown_tool_class:{tool_class}")
    if binding.get("allowlist_mutation"):
        errors.append("tool_allowlist_mutation")
    if binding.get("permission_granted"):
        errors.append("tool_permission_granted")
    return errors
