"""Validate Offer Builder output against frozen schema + semantic rules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from tests.support.archive_mkt_validation import validate_offer_output_semantics

from app.connectors.evidence import hash_payload
from app.product.offer_builder.contracts import SKILL_ID


def package_root() -> Path:
    return Path(__file__).resolve().parents[3] / "packages" / "skills" / SKILL_ID


def _schema_registry(root: Path) -> Registry:
    schema_dir = root / "schemas"
    parsed: dict[str, dict[str, Any]] = {}
    for path in sorted(schema_dir.glob("*.json")):
        parsed[path.name] = json.loads(path.read_text(encoding="utf-8"))
    resources: list[tuple[str, Resource[Any]]] = []
    seen: set[str] = set()

    def add(uri: str, resource: Resource[Any]) -> None:
        if uri not in seen:
            seen.add(uri)
            resources.append((uri, resource))

    for name, contents in parsed.items():
        resource = Resource.from_contents(contents)
        add(f"schemas/{name}", resource)
        schema_id = contents.get("$id")
        if isinstance(schema_id, str):
            add(schema_id, resource)
        for other_id in (
            item.get("$id") for item in parsed.values() if isinstance(item.get("$id"), str)
        ):
            add(urljoin(other_id, f"schemas/{name}"), resource)
    return Registry().with_resources(resources)


def validate_output_schema(data: dict[str, Any]) -> None:
    root = package_root()
    schema = json.loads((root / "schemas" / "output.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema, registry=_schema_registry(root)).validate(data)


def validate_output_semantics(
    data: dict[str, Any],
    *,
    mv_verdict: str,
    substantiated_claim_ids: set[str],
) -> list[str]:
    return validate_offer_output_semantics(
        data,
        mv_verdict=mv_verdict,
        substantiated_claim_ids=substantiated_claim_ids,
    )


def compute_output_hash(data: dict[str, Any]) -> str:
    payload = {k: v for k, v in data.items() if k != "output_hash"}
    return hash_payload(payload)
