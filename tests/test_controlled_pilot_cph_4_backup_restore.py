"""CPH.4 — unit tests for backup/restore guards (no destructive source ops)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.cph4_common import (
    EXPECTED_REVISION,
    Cph4Error,
    assert_restore_target,
    assert_source_db,
    sha256_file,
)
from scripts.cph4_verify_backup import verify_backup


def test_assert_source_db_ok() -> None:
    assert_source_db("botfazer_cph1")


def test_assert_source_db_rejects_other() -> None:
    with pytest.raises(SystemExit) as ei:
        assert_source_db("botfazer")
    assert "backup_source_database_mismatch" in str(ei.value)


@pytest.mark.parametrize(
    "name",
    ["botfazer", "botfazer_cph1", "postgres", "template0", "random_db", "botfazer_cph4"],
)
def test_unsafe_restore_targets_rejected(name: str) -> None:
    with pytest.raises(SystemExit) as ei:
        assert_restore_target(name)
    assert "restore_target_unsafe" in str(ei.value)


def test_disposable_restore_target_accepted() -> None:
    assert_restore_target("botfazer_cph4_restore_testrun1")


def test_checksum_and_manifest_roundtrip(tmp_path: Path) -> None:
    dump = tmp_path / "cph4_botfazer_cph1_test.dump"
    dump.write_bytes(b"PGDMP" + b"\x00" * 2048)
    digest = sha256_file(dump)
    manifest = {
        "backup_id": "cph4_botfazer_cph1_test",
        "filename": dump.name,
        "sha256": digest,
        "file_size": dump.stat().st_size,
        "source_revision": EXPECTED_REVISION,
        "source_database": "botfazer_cph1",
    }
    man_path = tmp_path / "cph4_botfazer_cph1_test.manifest.json"
    man_path.write_text(json.dumps(manifest), encoding="utf-8")
    result = verify_backup(man_path)
    assert result["ok"] is True
    assert result["sha256"] == digest


def test_checksum_rejects_corruption(tmp_path: Path) -> None:
    dump = tmp_path / "cph4_botfazer_cph1_test.dump"
    dump.write_bytes(b"PGDMP" + b"\x00" * 2048)
    digest = sha256_file(dump)
    manifest = {
        "backup_id": "x",
        "filename": dump.name,
        "sha256": digest,
        "file_size": dump.stat().st_size,
        "source_revision": EXPECTED_REVISION,
        "source_database": "botfazer_cph1",
    }
    man_path = tmp_path / "m.json"
    man_path.write_text(json.dumps(manifest), encoding="utf-8")
    # corrupt dump after manifest
    data = bytearray(dump.read_bytes())
    data[100] ^= 0xFF
    dump.write_bytes(bytes(data))
    with pytest.raises(SystemExit) as ei:
        verify_backup(man_path)
    assert "backup_checksum_failed" in str(ei.value)


def test_wrong_revision_rejected(tmp_path: Path) -> None:
    dump = tmp_path / "cph4_botfazer_cph1_test.dump"
    dump.write_bytes(b"PGDMP" + b"\x00" * 2048)
    digest = sha256_file(dump)
    manifest = {
        "backup_id": "x",
        "filename": dump.name,
        "sha256": digest,
        "file_size": dump.stat().st_size,
        "source_revision": "19990101_0000",
        "source_database": "botfazer_cph1",
    }
    man_path = tmp_path / "m.json"
    man_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(SystemExit) as ei:
        verify_backup(man_path)
    assert "backup_revision_mismatch" in str(ei.value)


def test_missing_manifest() -> None:
    with pytest.raises(SystemExit) as ei:
        verify_backup(Path("does_not_exist_cph4_manifest.json"))
    assert "backup_manifest_missing" in str(ei.value)
