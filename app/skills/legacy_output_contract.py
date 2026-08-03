"""Legacy output contract compatibility for frozen Skill package versions (SKILL-02.2.1).

Frozen packages predating output_contract_type remain byte-identical. Contract type is
resolved outside the package via explicit mapping until a new semver is published.
Remove entries when superseded (e.g. Market Validation 0.2.0).
"""

from __future__ import annotations

from app.schemas.contracts import SkillManifest, SkillOutputContractType

# skill_id + version → frozen SHA-256 content hash (immutable once published).
FROZEN_PACKAGE_HASHES: dict[tuple[str, str], str] = {
    (
        "ms.skill.product_marketing_context",
        "0.1.0",
    ): "5e3dfc1bfc48c56d33951006c3adcf80b4d53ad246e96669d1d32014934cc230",
    (
        "ms.skill.market_validation",
        "0.1.0",
    ): "6c53b5b972e5de900a135b891d8fbbd1641cdb5bf04bb171f83d5023344b8133",
    (
        "ms.skill.market_validation",
        "0.2.0",
    ): "ec7c86ce0bc39b5481e336b7749de3cf087d47630be315c639897dd687568f7a",
    (
        "ms.skill.positioning",
        "0.1.0",
    ): "cbd8283f4addaa9c8496504a9c6dbccd580e8ca317b2cf86bf628be6557e8da6",
}

# Legacy packages without manifest output_contract_type — resolved at validation time.
LEGACY_OUTPUT_CONTRACT_TYPES: dict[tuple[str, str], SkillOutputContractType] = {
    ("ms.skill.product_marketing_context", "0.1.0"): SkillOutputContractType.CONTEXT,
    ("ms.skill.market_validation", "0.1.0"): SkillOutputContractType.DECISION,
}


def resolve_output_contract_type(manifest: SkillManifest) -> SkillOutputContractType | None:
    """Return manifest field or legacy compatibility mapping."""
    if manifest.output_contract_type is not None:
        return manifest.output_contract_type
    return LEGACY_OUTPUT_CONTRACT_TYPES.get((manifest.id, manifest.version))


def expected_frozen_package_hash(skill_id: str, version: str) -> str | None:
    return FROZEN_PACKAGE_HASHES.get((skill_id, version))


def frozen_package_hash_conflict(
    *,
    skill_id: str,
    version: str,
    package_hash: str,
) -> str | None:
    """Return error message when a frozen version's hash changed (blocking conflict)."""
    expected = expected_frozen_package_hash(skill_id, version)
    if expected is None:
        return None
    if package_hash == expected:
        return None
    return (
        f"Immutable version conflict: {skill_id}@{version} hash {package_hash} "
        f"does not match frozen hash {expected}."
    )


__all__ = [
    "FROZEN_PACKAGE_HASHES",
    "LEGACY_OUTPUT_CONTRACT_TYPES",
    "expected_frozen_package_hash",
    "frozen_package_hash_conflict",
    "resolve_output_contract_type",
]
