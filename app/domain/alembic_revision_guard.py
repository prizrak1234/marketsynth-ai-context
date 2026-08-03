"""CPH.1 — Alembic revision diagnostics (read-only; never auto-stamps)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class DatabaseRevisionState(StrEnum):
    CURRENT = "current"
    BEHIND = "behind"
    AHEAD = "ahead"
    UNKNOWN = "database_revision_unknown"
    MISSING_FROM_TREE = "database_revision_missing_from_tree"
    MULTIPLE_HEADS = "multiple_heads"
    NO_VERSION_TABLE = "no_version_table"
    EMPTY = "empty"


@dataclass(frozen=True)
class RevisionDiagnostic:
    code_heads: tuple[str, ...]
    database_revisions: tuple[str, ...]
    state: DatabaseRevisionState
    detail: str
    auto_stamp_allowed: bool = False
    auto_migrate_allowed: bool = False


def list_code_revisions(versions_dir: Path | None = None) -> dict[str, str | None]:
    """Return {revision_id: down_revision} from local alembic scripts."""
    root = versions_dir or (Path(__file__).resolve().parents[2] / "alembic" / "versions")
    out: dict[str, str | None] = {}
    for path in sorted(root.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        rev = None
        down: str | None = None
        for line in text.splitlines():
            if line.startswith("revision:") and "=" in line:
                rev = line.split("=", 1)[1].strip().strip("'\"")
            if line.startswith("down_revision:"):
                raw = line.split("=", 1)[1].strip()
                if raw in ("None", "none"):
                    down = None
                else:
                    # handle Union typing line: down_revision: Union[str, None] = "x"
                    if '"' in raw:
                        down = raw.split('"')[1]
                    elif "'" in raw:
                        down = raw.split("'")[1]
                    else:
                        down = None
        if rev:
            out[rev] = down
    return out


def classify_revision(
    *,
    database_revisions: list[str] | tuple[str, ...] | None,
    code_heads: list[str] | tuple[str, ...] | None = None,
    code_revisions: dict[str, str | None] | None = None,
) -> RevisionDiagnostic:
    code_map = code_revisions or list_code_revisions()
    heads = tuple(code_heads) if code_heads is not None else _compute_heads(code_map)
    db_revs = tuple(database_revisions or ())

    if len(heads) > 1:
        return RevisionDiagnostic(
            code_heads=heads,
            database_revisions=db_revs,
            state=DatabaseRevisionState.MULTIPLE_HEADS,
            detail="Multiple Alembic heads in code tree",
        )
    if not db_revs:
        return RevisionDiagnostic(
            code_heads=heads,
            database_revisions=(),
            state=DatabaseRevisionState.EMPTY,
            detail="No alembic_version rows",
        )

    unknown = [r for r in db_revs if r not in code_map]
    if unknown:
        return RevisionDiagnostic(
            code_heads=heads,
            database_revisions=db_revs,
            state=DatabaseRevisionState.MISSING_FROM_TREE,
            detail=(
                "Database revision(s) absent from local migration tree: "
                + ", ".join(unknown)
                + ". Do not alembic stamp head."
            ),
        )

    if heads and set(db_revs) == set(heads):
        return RevisionDiagnostic(
            code_heads=heads,
            database_revisions=db_revs,
            state=DatabaseRevisionState.CURRENT,
            detail="Database matches code head",
        )

    # simplistic ancestry: if db is ancestor of head → behind
    head = heads[0] if heads else None
    if head and all(_is_ancestor(code_map, parent=r, of=head) for r in db_revs):
        return RevisionDiagnostic(
            code_heads=heads,
            database_revisions=db_revs,
            state=DatabaseRevisionState.BEHIND,
            detail="Database is behind code head",
        )
    if head and all(_is_ancestor(code_map, parent=head, of=r) for r in db_revs):
        return RevisionDiagnostic(
            code_heads=heads,
            database_revisions=db_revs,
            state=DatabaseRevisionState.AHEAD,
            detail="Database appears ahead of code head",
        )
    return RevisionDiagnostic(
        code_heads=heads,
        database_revisions=db_revs,
        state=DatabaseRevisionState.UNKNOWN,
        detail="Unable to classify revision relationship",
    )


def _compute_heads(code_map: dict[str, str | None]) -> tuple[str, ...]:
    downs = {d for d in code_map.values() if d}
    return tuple(sorted(r for r in code_map if r not in downs))


def _is_ancestor(code_map: dict[str, str | None], *, parent: str, of: str) -> bool:
    seen: set[str] = set()
    cur: str | None = of
    while cur and cur not in seen:
        if cur == parent:
            return True
        seen.add(cur)
        cur = code_map.get(cur)
    return False


def is_revision_in_chain(
    revision: str,
    *,
    head: str | None = None,
    code_revisions: dict[str, str | None] | None = None,
) -> bool:
    """True when *revision* exists in the migration tree and is on the path to *head*."""
    code_map = code_revisions or list_code_revisions()
    if revision not in code_map:
        return False
    target_head = head
    if target_head is None:
        heads = _compute_heads(code_map)
        if len(heads) != 1:
            return False
        target_head = heads[0]
    return revision == target_head or _is_ancestor(code_map, parent=revision, of=target_head)
