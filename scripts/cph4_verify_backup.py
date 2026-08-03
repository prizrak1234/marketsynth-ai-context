"""CPH.4 — verify backup file exists and SHA-256 matches manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.cph4_common import (
    EXPECTED_REVISION,
    Cph4Error,
    default_backup_root,
    sha256_file,
)


def verify_backup(manifest_path: Path, *, expect_revision: str = EXPECTED_REVISION) -> dict:
    if not manifest_path.is_file():
        raise Cph4Error("backup_manifest_missing", str(manifest_path))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dump = manifest_path.parent / manifest["filename"]
    if not dump.is_file():
        raise Cph4Error("backup_file_missing", str(dump))
    digest = sha256_file(dump)
    if digest != manifest.get("sha256"):
        raise Cph4Error(
            "backup_checksum_failed",
            f"expected={manifest.get('sha256')} actual={digest}",
        )
    if manifest.get("source_revision") != expect_revision:
        raise Cph4Error(
            "backup_revision_mismatch",
            f"manifest={manifest.get('source_revision')} expected={expect_revision}",
        )
    size = dump.stat().st_size
    if size != int(manifest.get("file_size", -1)):
        raise Cph4Error("backup_checksum_failed", f"size_mismatch actual={size}")
    if size < 1024:
        raise Cph4Error("backup_checksum_failed", "file_too_small")
    return {
        "ok": True,
        "backup_id": manifest["backup_id"],
        "sha256": digest,
        "file_size": size,
        "source_revision": manifest["source_revision"],
        "source_database": manifest["source_database"],
        "path": str(dump),
        "manifest_path": str(manifest_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="CPH.4 verify backup checksum")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--expect-revision", default=EXPECTED_REVISION)
    args = parser.parse_args()
    try:
        result = verify_backup(Path(args.manifest), expect_revision=args.expect_revision)
        print(json.dumps(result, indent=2))
        return 0
    except Cph4Error as exc:
        print(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
