"""Deterministic Skill package content hashing (SKILL-01.2)."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from app.skills.errors import SkillHashingError, SkillPackagePathViolationError

# Matches SKILL-01.0 freeze audit algorithm (docs/rfc/SKILL-01-0-freeze-audit.md).
HASH_ALGORITHM = "sha256"

# Nested semver directories (e.g. 0.2.0/) hold alternate immutable versions and are
# excluded from the parent package root hash so frozen 0.1.0 lineage stays stable.
_NESTED_VERSION_DIR = re.compile(r"^\d+\.\d+\.\d+(?:/|$)")


def _exclude_from_parent_package_hash(rel_posix: str) -> bool:
    return bool(_NESTED_VERSION_DIR.match(rel_posix))


def calculate_skill_package_hash(package_path: Path) -> str:
    """Return SHA-256 over sorted relative POSIX paths concatenated with raw file bytes."""
    root = package_path.resolve()
    if not root.is_dir():
        raise SkillHashingError("Package root is not a directory.")

    digest = hashlib.sha256()
    file_paths: list[Path] = []

    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise SkillPackagePathViolationError(
                "Symlinks are forbidden in Skill packages for hashing."
            )
        if not path.is_file():
            continue
        try:
            rel_posix = path.resolve().relative_to(root).as_posix()
        except ValueError as exc:
            raise SkillPackagePathViolationError(
                "File path escapes package root during hashing."
            ) from exc
        if _exclude_from_parent_package_hash(rel_posix):
            continue
        file_paths.append(path)

    for path in file_paths:
        rel = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(rel)
        digest.update(path.read_bytes())

    return digest.hexdigest()
