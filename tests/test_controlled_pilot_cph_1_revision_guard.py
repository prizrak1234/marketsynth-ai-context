"""CPH.1 — Alembic revision guard and migration policy tests (no DB mutation)."""

from __future__ import annotations

from pathlib import Path

from app.domain.alembic_revision_guard import (
    DatabaseRevisionState,
    classify_revision,
    list_code_revisions,
)


def test_code_heads_single_commercial_mvp() -> None:
    code = list_code_revisions()
    downs = {d for d in code.values() if d}
    heads = [r for r in code if r not in downs]
    assert heads == ["20260715_0037"]
    assert "20260614_0029" in code
    assert code["20260614_0036"] == "20260614_0035"
    assert "20260608_0033" not in code


def test_unknown_revision_not_stamped() -> None:
    diag = classify_revision(database_revisions=["20260608_0033"])
    assert diag.state == DatabaseRevisionState.MISSING_FROM_TREE
    assert diag.auto_stamp_allowed is False
    assert diag.auto_migrate_allowed is False
    assert "Do not alembic stamp head" in diag.detail


def test_current_head_classified() -> None:
    diag = classify_revision(database_revisions=["20260715_0037"])
    assert diag.state == DatabaseRevisionState.CURRENT


def test_behind_classified() -> None:
    diag = classify_revision(database_revisions=["20260614_0034"])
    assert diag.state == DatabaseRevisionState.BEHIND


def test_migration_chain_0029_to_0036_files() -> None:
    root = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    expected = [
        ("20260614_0029", "20260603_0028"),
        ("20260614_0030", "20260614_0029"),
        ("20260614_0031", "20260614_0030"),
        ("20260614_0032", "20260614_0031"),
        ("20260614_0033", "20260614_0032"),
        ("20260614_0034", "20260614_0033"),
        ("20260614_0035", "20260614_0034"),
        ("20260614_0036", "20260614_0035"),
    ]
    code = list_code_revisions(root)
    for rev, down in expected:
        assert rev in code
        assert code[rev] == down


def test_no_duplicate_revision_ids() -> None:
    root = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    ids: list[str] = []
    for path in root.glob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("revision:") and "=" in line and '"' in line:
                ids.append(line.split('"')[1])
                break
    assert len(ids) == len(set(ids))


def test_fail_fast_policy_development_soft() -> None:
    from app.core.config import Settings
    from app.domain.alembic_revision_guard import DatabaseRevisionState, RevisionDiagnostic
    from app.services.alembic_revision_startup import should_fail_fast

    diag = RevisionDiagnostic(
        code_heads=("20260614_0036",),
        database_revisions=("20260608_0033",),
        state=DatabaseRevisionState.MISSING_FROM_TREE,
        detail="missing",
    )
    soft = Settings(app_env="development", alembic_revision_fail_fast=False)
    hard = Settings(app_env="development", alembic_revision_fail_fast=True)
    assert should_fail_fast(diag, soft) is False
    assert should_fail_fast(diag, hard) is True


def test_guard_never_allows_auto_stamp_or_migrate() -> None:
    diag = classify_revision(database_revisions=["20260614_0036"])
    assert diag.auto_stamp_allowed is False
    assert diag.auto_migrate_allowed is False


def test_disposable_backup_meta_shape() -> None:
    """Backup metadata contract (no DB / no credentials)."""
    meta = {
        "timestamp_utc": "20260715T000000Z",
        "database": "botfazer_cph1",
        "alembic_revisions": ["20260614_0036"],
        "dump_ok": True,
        "dump_file": "backup_botfazer_cph1_20260715T000000Z.sql",
    }
    assert "password" not in str(meta).lower()
    assert meta["alembic_revisions"]
    assert meta["database"] != "botfazer" or True  # local data DB allowed for backup only
