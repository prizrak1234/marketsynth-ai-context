"""Quarantine workspace path helpers (SKILL-01.4)."""

from __future__ import annotations

import uuid
from pathlib import Path

from app.skills.quarantine_errors import SkillQuarantinePathViolationError


def is_local_path(path: Path) -> bool:
    value = str(path).lower()
    return not value.startswith(("http://", "https://", "git://", "ssh://", "ftp://"))


def resolve_local_source(path: Path) -> Path:
    if not is_local_path(path):
        raise SkillQuarantinePathViolationError("Remote source paths are forbidden.")
    resolved = path.resolve()
    if not resolved.exists():
        raise SkillQuarantinePathViolationError("Source path does not exist.")
    return resolved


def generate_import_id() -> str:
    return str(uuid.uuid4())


def quarantine_workspace_root(base_dir: Path, import_id: str) -> Path:
    return base_dir / import_id


def normalized_package_root(workspace: Path) -> Path:
    return workspace / "normalized"


def source_snapshot_root(workspace: Path) -> Path:
    return workspace / "source"


def reports_root(workspace: Path) -> Path:
    return workspace / "reports"


def ensure_within_root(root: Path, target: Path) -> Path:
    resolved_root = root.resolve()
    resolved_target = target.resolve()
    try:
        resolved_target.relative_to(resolved_root)
    except ValueError as exc:
        raise SkillQuarantinePathViolationError("Path escapes quarantine root.") from exc
    return resolved_target


def safe_relative_path(root: Path, target: Path) -> str:
    rel = ensure_within_root(root, target).relative_to(root.resolve())
    return rel.as_posix()
