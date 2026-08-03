"""Static inspection for quarantine import (SKILL-01.4)."""

from __future__ import annotations

import re
from pathlib import Path

from app.skills.hashing import calculate_skill_package_hash
from app.skills.quarantine_contracts import (
    QuarantineImportLimits,
    QuarantineStaticFinding,
    QuarantineStaticFindingSeverity,
)
from app.skills.quarantine_errors import (
    SkillQuarantineLimitExceededError,
    SkillQuarantinePathViolationError,
    SkillQuarantineUnsupportedFileError,
)

EXECUTABLE_SUFFIXES = frozenset(
    {
        ".sh",
        ".bash",
        ".py",
        ".js",
        ".ts",
        ".mjs",
        ".cjs",
        ".exe",
        ".bat",
        ".cmd",
        ".ps1",
        ".pl",
        ".rb",
        ".dll",
        ".so",
        ".dylib",
    }
)
BINARY_SUFFIXES = frozenset({".exe", ".dll", ".so", ".dylib", ".bin", ".dat"})
SECRET_FILENAME_PATTERNS = re.compile(
    r"(\.env$|\.pem$|\.key$|id_rsa|credentials|secrets?\.|token)",
    re.IGNORECASE,
)
ARCHIVE_SUFFIXES = frozenset({".zip", ".tar", ".gz", ".tgz", ".7z", ".rar"})


def calculate_source_fingerprint(root: Path) -> str:
    return calculate_skill_package_hash(root)


def _iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise SkillQuarantinePathViolationError("Symlinks are forbidden in source package.")
        if path.is_file():
            files.append(path)
    return files


def inspect_source_tree(
    root: Path,
    *,
    limits: QuarantineImportLimits,
) -> tuple[list[QuarantineStaticFinding], int, int]:
    findings: list[QuarantineStaticFinding] = []
    total_bytes = 0
    files = _iter_files(root)
    if len(files) > limits.max_file_count:
        raise SkillQuarantineLimitExceededError(
            f"File count {len(files)} exceeds limit {limits.max_file_count}."
        )

    seen_names: dict[str, str] = {}
    for path in files:
        rel = path.relative_to(root)
        depth = len(rel.parts)
        if depth > limits.max_directory_depth:
            raise SkillQuarantineLimitExceededError(
                f"Directory depth {depth} exceeds limit {limits.max_directory_depth}."
            )
        if len(rel.as_posix()) > limits.max_path_length:
            raise SkillQuarantineLimitExceededError("Path length exceeds configured limit.")

        lower_name = rel.name.lower()
        if lower_name in seen_names and lower_name != rel.name:
            findings.append(
                QuarantineStaticFinding(
                    code="case_collision_filename",
                    severity=QuarantineStaticFindingSeverity.WARNING,
                    message="Case-conflicting filename detected.",
                    location=rel.as_posix(),
                )
            )
        seen_names[lower_name] = rel.as_posix()

        size = path.stat().st_size
        total_bytes += size
        if size > limits.max_single_file_bytes:
            raise SkillQuarantineLimitExceededError(
                f"File {rel.as_posix()} exceeds single-file size limit."
            )

        suffix = path.suffix.lower()
        if suffix in ARCHIVE_SUFFIXES:
            findings.append(
                QuarantineStaticFinding(
                    code="nested_archive",
                    severity=QuarantineStaticFindingSeverity.ERROR,
                    message="Nested archives are forbidden in quarantine import.",
                    location=rel.as_posix(),
                    rule_reference="RFC-SKILL-003",
                )
            )
        if suffix in EXECUTABLE_SUFFIXES:
            findings.append(
                QuarantineStaticFinding(
                    code="executable_script",
                    severity=QuarantineStaticFindingSeverity.ERROR,
                    message="Executable script file detected.",
                    location=rel.as_posix(),
                    rule_reference="RFC-SKILL-003",
                )
            )
        if suffix in BINARY_SUFFIXES:
            findings.append(
                QuarantineStaticFinding(
                    code="unsupported_binary",
                    severity=QuarantineStaticFindingSeverity.ERROR,
                    message="Unsupported binary payload detected.",
                    location=rel.as_posix(),
                    rule_reference="RFC-SKILL-003",
                )
            )
        if SECRET_FILENAME_PATTERNS.search(rel.as_posix()):
            findings.append(
                QuarantineStaticFinding(
                    code="secret_like_filename",
                    severity=QuarantineStaticFindingSeverity.ERROR,
                    message="Secret-like filename detected.",
                    location=rel.as_posix(),
                    rule_reference="RFC-SKILL-003",
                )
            )
        if rel.name.startswith(".") and rel.name not in {".gitkeep"}:
            findings.append(
                QuarantineStaticFinding(
                    code="hidden_file",
                    severity=QuarantineStaticFindingSeverity.WARNING,
                    message="Hidden file detected.",
                    location=rel.as_posix(),
                )
            )

    if total_bytes > limits.max_total_bytes:
        raise SkillQuarantineLimitExceededError("Total package size exceeds configured limit.")

    return findings, total_bytes, len(files)


def materialize_package(
    source_root: Path,
    destination_root: Path,
    *,
    limits: QuarantineImportLimits,
) -> None:
    if destination_root.exists():
        raise SkillQuarantineUnsupportedFileError("Quarantine destination already exists.")

    destination_root.mkdir(parents=True, exist_ok=False)
    files = _iter_files(source_root)
    if len(files) > limits.max_file_count:
        raise SkillQuarantineLimitExceededError("File count exceeds limit during materialization.")

    for src in files:
        rel = src.relative_to(source_root)
        dst = destination_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
