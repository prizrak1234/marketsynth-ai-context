"""Safe manifest.yaml parsing for Skill packages (SKILL-01.2)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from app.schemas.contracts import SkillManifest
from app.skills.errors import (
    SkillManifestMissingError,
    SkillManifestParseError,
    SkillManifestValidationError,
)

_MULTI_DOC_PATTERN = re.compile(r"(?m)^---\s*$")
_ANCHOR_ALIAS_PATTERN = re.compile(r"(?m)(?:^|\s)[&*][A-Za-z0-9_-]+")
_CUSTOM_TAG_PATTERN = re.compile(r"!![A-Za-z0-9_.-]+")

_STRING_ENUM_FIELDS = frozenset({"status", "source", "license", "tenant_scope", "version", "id"})


class StrictManifestLoader(yaml.SafeLoader):
    """SafeLoader with duplicate-key and alias rejection."""


def _construct_mapping(
    loader: StrictManifestLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[str, Any]:
    if getattr(node, "anchor", None) is not None:
        raise SkillManifestParseError("YAML anchors are forbidden in manifest.yaml.")
    mapping: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise SkillManifestParseError(
                f"Manifest mapping keys must be strings; got {type(key).__name__}."
            )
        if key in mapping:
            raise SkillManifestParseError(f"Duplicate manifest key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


def _reject_custom_tag(loader: StrictManifestLoader, tag_suffix: str, node: yaml.Node) -> Any:
    raise SkillManifestParseError(f"Custom YAML tags are forbidden: !{tag_suffix}")


def _reject_merge(loader: StrictManifestLoader, node: yaml.Node) -> Any:
    raise SkillManifestParseError("YAML merge keys are forbidden in manifest.yaml.")


StrictManifestLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)
StrictManifestLoader.add_constructor("tag:yaml.org,2002:map", _construct_mapping)
StrictManifestLoader.add_constructor(None, _reject_custom_tag)
StrictManifestLoader.add_constructor("tag:yaml.org,2002:merge", _reject_merge)


def construct_object_no_aliases(
    self: StrictManifestLoader,
    node: yaml.Node,
    deep: bool = False,
) -> Any:
    if node.__class__.__name__ == "AliasNode":
        raise SkillManifestParseError("YAML aliases are forbidden in manifest.yaml.")
    return yaml.constructor.SafeConstructor.construct_object(self, node, deep=deep)


StrictManifestLoader.construct_object = construct_object_no_aliases  # type: ignore[method-assign]


def _inspect_raw_manifest(raw_text: str) -> None:
    if _MULTI_DOC_PATTERN.search(raw_text):
        raise SkillManifestParseError("Multiple YAML documents are forbidden in manifest.yaml.")
    if _ANCHOR_ALIAS_PATTERN.search(raw_text):
        raise SkillManifestParseError("YAML anchors and aliases are forbidden in manifest.yaml.")
    if _CUSTOM_TAG_PATTERN.search(raw_text):
        raise SkillManifestParseError("Custom YAML tags are forbidden in manifest.yaml.")


def _guard_string_enum_coercion(data: dict[str, Any]) -> None:
    for field in _STRING_ENUM_FIELDS:
        if field in data and not isinstance(data[field], str):
            raise SkillManifestParseError(
                f"Manifest field '{field}' must be a string; got {type(data[field]).__name__}."
            )


def parse_manifest_bytes(raw_bytes: bytes) -> dict[str, Any]:
    """Parse manifest bytes into a dict without domain validation."""
    raw_text = raw_bytes.decode("utf-8")
    _inspect_raw_manifest(raw_text)
    try:
        documents = list(yaml.load_all(raw_text, Loader=StrictManifestLoader))
    except SkillManifestParseError:
        raise
    except yaml.YAMLError as exc:
        raise SkillManifestParseError(f"Invalid YAML in manifest.yaml: {exc}") from exc

    if len(documents) != 1:
        raise SkillManifestParseError("manifest.yaml must contain exactly one YAML document.")
    data = documents[0]
    if not isinstance(data, dict):
        raise SkillManifestParseError("manifest.yaml root must be a mapping.")
    _guard_string_enum_coercion(data)
    return data


def parse_skill_manifest(path: Path) -> SkillManifest:
    """Parse manifest.yaml through safe YAML loading and canonical domain contracts."""
    if not path.is_file():
        raise SkillManifestMissingError(f"manifest.yaml not found at {path.name}.")
    data = parse_manifest_bytes(path.read_bytes())
    try:
        return SkillManifest.model_validate(data)
    except ValidationError as exc:
        raise SkillManifestValidationError(str(exc)) from exc
