"""CPH.4 — full restore drill orchestrator (backup → restore → verify → smoke)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.cph4_common import (  # noqa: E402
    EXPECTED_REVISION,
    Cph4Error,
    default_backup_root,
    now_iso,
    utc_stamp,
)


def run_step(label: str, args: list[str], *, env: dict | None = None) -> dict:
    print(f"\n=== {label} ===")
    t0 = time.perf_counter()
    merged = os.environ.copy()
    if env:
        merged.update(env)
    proc = subprocess.run(
        args,
        cwd=str(ROOT),
        env=merged,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = round(time.perf_counter() - t0, 3)
    print(proc.stdout)
    if proc.returncode != 0:
        print(proc.stderr[:800] if proc.stderr else "")
        raise Cph4Error("restore_failed", f"step={label} exit={proc.returncode}")
    return {"label": label, "seconds": elapsed, "stdout_tail": (proc.stdout or "")[-1500:]}


def corrupt_copy(dump_path: Path, out_path: Path) -> Path:
    data = bytearray(dump_path.read_bytes())
    if len(data) < 64:
        raise Cph4Error("backup_file_missing", "source_dump_too_small")
    # Flip middle bytes without touching the real backup
    mid = len(data) // 2
    data[mid] ^= 0xFF
    data[mid + 1] ^= 0xAA
    out_path.write_bytes(bytes(data))
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="CPH.4 restore drill")
    parser.add_argument("--out", default=str(default_backup_root()))
    parser.add_argument("--skip-smoke", action="store_true")
    parser.add_argument("--keep-restore-db", action="store_true")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()

    run_id = args.run_id or utc_stamp().lower()
    target = f"botfazer_cph4_restore_{run_id}"
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / f"cph4_drill_result_{run_id}.json"
    timings: dict[str, float] = {}
    t_total = time.perf_counter()

    try:
        # 1) Backup
        step = run_step(
            "backup",
            [
                sys.executable,
                "-m",
                "scripts.cph4_backup_pilot_db",
                "--out",
                str(out_dir),
                "--require-db",
                "botfazer_cph1",
            ],
        )
        timings["backup"] = step["seconds"]

        manifests = sorted(out_dir.glob("cph4_botfazer_cph1_*.manifest.json"))
        if not manifests:
            raise Cph4Error("backup_manifest_missing", str(out_dir))
        manifest = manifests[-1]

        # 2) Verify checksum
        step = run_step(
            "verify_backup",
            [
                sys.executable,
                "-m",
                "scripts.cph4_verify_backup",
                "--manifest",
                str(manifest),
                "--expect-revision",
                EXPECTED_REVISION,
            ],
        )
        timings["checksum"] = step["seconds"]

        # 3) Corrupted backup rejection
        man = json.loads(manifest.read_text(encoding="utf-8"))
        dump = manifest.parent / man["filename"]
        bad_dump = out_dir / f"CORRUPT_{man['filename']}"
        corrupt_copy(dump, bad_dump)
        bad_manifest = out_dir / f"CORRUPT_{manifest.name}"
        bad_man = dict(man)
        bad_man["filename"] = bad_dump.name
        # Keep original checksum so verify fails
        bad_manifest.write_text(json.dumps(bad_man, indent=2), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.cph4_verify_backup",
                "--manifest",
                str(bad_manifest),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 or "backup_checksum_failed" not in (proc.stdout + proc.stderr):
            raise Cph4Error("backup_checksum_failed", "corrupt_copy_was_accepted")
        print("corrupted_backup_rejected=True")

        # Wrong checksum field
        wrong = dict(man)
        wrong["sha256"] = "0" * 64
        wrong_path = out_dir / f"WRONGHASH_{manifest.name}"
        wrong_path.write_text(json.dumps(wrong, indent=2), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, "-m", "scripts.cph4_verify_backup", "--manifest", str(wrong_path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            raise Cph4Error("backup_checksum_failed", "wrong_hash_accepted")

        # Unsafe target rejection
        for bad_target in ("botfazer", "botfazer_cph1", "postgres", "not_approved_db"):
            proc = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from scripts.cph4_common import assert_restore_target, Cph4Error\n"
                    f"try:\n assert_restore_target({bad_target!r})\n print('accepted')\n"
                    "except SystemExit as e:\n print(e)",
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            if "accepted" in proc.stdout:
                raise Cph4Error("restore_target_unsafe", f"accepted_{bad_target}")
        print("unsafe_targets_rejected=True")

        # 4) Restore
        env = {"CPH4_CONFIRM_RESTORE": "1"}
        step = run_step(
            "restore",
            [
                sys.executable,
                "-m",
                "scripts.cph4_restore_disposable",
                "--manifest",
                str(manifest),
                "--target",
                target,
            ],
            env=env,
        )
        timings["restore_total"] = step["seconds"]

        # 5) Verify + session policy + smoke
        smoke_args = [
            sys.executable,
            "-m",
            "scripts.cph4_verify_restored_db",
            "--manifest",
            str(manifest),
            "--target",
            target,
        ]
        if args.skip_smoke:
            smoke_args.append("--skip-smoke")
        step = run_step("verify_restored", smoke_args, env=env)
        timings["verify_and_smoke"] = step["seconds"]

        # Parse verify output for nest
        verify_json = {}
        for line in reversed(step["stdout_tail"].splitlines()):
            if line.strip().startswith("{"):
                # find full JSON in stdout - re-run parse from file better
                break
        # Extract JSON block from last step by re-reading - store in file from verify
        # For robustness, write verify to result by parsing stdout
        try:
            raw = step["stdout_tail"]
            start = raw.find("{")
            end = raw.rfind("}")
            if start >= 0 and end > start:
                verify_json = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            verify_json = {"parse_warning": True}

        # Update manifest restore fields
        man["restore_test_status"] = "passed"
        man["restore_database"] = target
        man["restore_verified_at"] = now_iso()
        manifest.write_text(json.dumps(man, indent=2, ensure_ascii=False), encoding="utf-8")

        # Wrong revision detection (unit-style on existing verify)
        man_bad_rev = dict(man)
        man_bad_rev["source_revision"] = "19990101_0000"
        bad_rev_path = out_dir / f"BADREV_{manifest.name}"
        bad_rev_path.write_text(json.dumps(man_bad_rev, indent=2), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.cph4_verify_backup",
                "--manifest",
                str(bad_rev_path),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        wrong_rev_ok = proc.returncode != 0 and "backup_revision_mismatch" in (
            proc.stdout + proc.stderr
        )
        print("wrong_revision_rejected=", wrong_rev_ok)

        timings["total_recovery"] = round(time.perf_counter() - t_total, 3)

        result = {
            "ok": True,
            "run_id": run_id,
            "manifest": str(manifest),
            "backup_id": man["backup_id"],
            "sha256": man["sha256"],
            "file_size": man["file_size"],
            "source_database": man["source_database"],
            "source_revision": man["source_revision"],
            "restore_database": target,
            "expected_revision": EXPECTED_REVISION,
            "corrupted_backup_rejected": True,
            "unsafe_targets_rejected": True,
            "wrong_revision_rejected": wrong_rev_ok,
            "verify": verify_json,
            "timings_seconds": timings,
            "session_policy": "A_revoke_all_after_restore",
            "completed_at": now_iso(),
        }
        result_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
        print("\n=== DRILL RESULT ===")
        print(json.dumps(result, indent=2, default=str))
        print("result_file=", result_path)

        if not args.keep_restore_db:
            drop = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import asyncio\n"
                    "from scripts.cph4_restore_disposable import drop_restore_db\n"
                    f"asyncio.run(drop_restore_db({target!r}))\n",
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            print("cleanup_drop=", drop.returncode, (drop.stdout or drop.stderr or "")[:300])

        return 0
    except Cph4Error as exc:
        print(str(exc))
        fail = {
            "ok": False,
            "error": str(exc),
            "run_id": run_id,
            "target": target,
            "completed_at": now_iso(),
        }
        result_path.write_text(json.dumps(fail, indent=2), encoding="utf-8")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
