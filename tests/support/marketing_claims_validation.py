"""Test helpers for ARCHIVE-MKT-01.1 marketing claims shared schemas."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parents[2]
CLAIMS_ROOT = REPO_ROOT / "packages" / "knowledge" / "marketing_claims" / "0.1.0"
FROZEN_BUNDLE_HASH = "c29ca2c08ccbb8861206fcc855e966c93d50b68264d8d9bdd096e13cd5c32f8d"
CANONICAL_URI_BASE = "https://schemas.marketsynth.ai/marketing-claims/0.1.0/"

PROHIBITED_PATTERNS = (
    r"100%\s*guaranteed\s*income",
    r"100%\s*safety",
    r"zero\s*risk",
    r"technology\s+cannot\s+fail",
)

FINANCIAL_CLAIM_TYPES = {"income_or_financial", "savings", "pricing"}
SAFETY_CLAIM_TYPES = {"safety", "guarantee"}


def load_freeze_manifest() -> dict[str, Any]:
    return json.loads((CLAIMS_ROOT / "freeze_manifest.json").read_text(encoding="utf-8"))


def _schema_registry() -> Registry:
    resources: list[tuple[str, Resource[Any]]] = []
    for path in sorted(CLAIMS_ROOT.glob("*.schema.json")):
        contents = json.loads(path.read_text(encoding="utf-8"))
        resource = Resource.from_contents(contents)
        resources.append((path.name, resource))
        schema_id = contents.get("$id")
        if isinstance(schema_id, str):
            resources.append((schema_id, resource))
    return Registry().with_resources(resources)


def schema_validator(schema_name: str) -> Draft202012Validator:
    schema = json.loads((CLAIMS_ROOT / schema_name).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=_schema_registry())


def validate_marketing_claim(data: dict[str, Any]) -> None:
    schema_validator("marketing-claim.schema.json").validate(data)


def validate_promise_candidate(data: dict[str, Any]) -> None:
    schema_validator("promise-candidate.schema.json").validate(data)


def validate_risk_reversal(data: dict[str, Any]) -> None:
    schema_validator("risk-reversal.schema.json").validate(data)


def validate_marketing_claim_semantics(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    statement = data.get("statement", "")
    claim_type = data.get("claim_type")
    verification = data.get("verification_status")
    substantiation = data.get("substantiation_status")
    evidence = data.get("evidence_references", [])
    assumptions = data.get("assumptions", [])

    if verification == "verified" and not evidence:
        errors.append("verified claim without evidence rejected")

    if claim_type in FINANCIAL_CLAIM_TYPES and not data.get("legal_review_required"):
        errors.append("financial claim requires legal review")

    if claim_type == "income_or_financial" and not data.get("human_review_required"):
        errors.append("financial outcome claim requires human review")

    for pattern in PROHIBITED_PATTERNS:
        if re.search(pattern, statement, re.IGNORECASE) and not data.get("prohibited"):
            errors.append(f"prohibited pattern in statement: {pattern}")

    if claim_type == "statistical" and not evidence:
        errors.append("statistical claim without source rejected")

    if claim_type == "comparative" and not data.get("conditions"):
        errors.append("comparative claim without comparison basis rejected")

    if verification == "verified" and assumptions:
        errors.append("assumption cannot become verified")

    if substantiation == "unsupported" and data.get("customer_facing_recommendation"):
        errors.append("unsupported claim cannot become customer-facing recommendation")

    return errors


def validate_promise_semantics(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    statement = data.get("proposed_statement", "")
    substantiation = data.get("substantiation_status")

    for pattern in PROHIBITED_PATTERNS:
        if re.search(pattern, statement, re.IGNORECASE) and not data.get("prohibited"):
            errors.append(f"prohibited promise pattern: {pattern}")

    if substantiation == "unsupported" and data.get("customer_facing"):
        errors.append("unsupported promise cannot be customer-facing")

    if data.get("claim_type") == "income_or_financial" and not data.get("human_review_required"):
        errors.append("financial promise requires review")

    return errors


def validate_risk_reversal_semantics(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("proves_outcome") is True:
        errors.append("risk reversal does not imply guaranteed result")
    if data.get("proves_outcome") is not False:
        errors.append("risk_reversal.proves_outcome must be false")
    return errors


def recompute_bundle_hash() -> str:
    manifest = load_freeze_manifest()
    payload = json.dumps(manifest["file_hashes"], sort_keys=True, separators=(",", ":"))
    import hashlib

    return hashlib.sha256(payload.encode()).hexdigest()


def bundle_has_remote_refs() -> list[str]:
    offenders: list[str] = []
    for path in CLAIMS_ROOT.glob("*.schema.json"):
        text = path.read_text(encoding="utf-8")
        if "http://" in text and "schemas.marketsynth.ai" not in text:
            offenders.append(path.name)
        if '"$ref": "http' in text.replace(CANONICAL_URI_BASE, "") and re.search(
            r'"\$ref":\s*"https?://(?!schemas\.marketsynth\.ai)', text
        ):
            offenders.append(path.name)
    return offenders
