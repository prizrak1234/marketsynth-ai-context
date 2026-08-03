"""Safe product skill package importer — no script execution."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from app.product_skills.catalog import BUILTIN_PRODUCT_SKILLS, get_builtin_manifest
from app.schemas.contracts import ProductSkillManifest

_FORBIDDEN_NAMES = {
    ".env",
    ".env.local",
    ".ds_store",
    "__pycache__",
}
_FORBIDDEN_SUFFIXES = {".pyc", ".exe", ".bat", ".cmd", ".ps1", ".sh"}
_SECRET_PATTERN = re.compile(
    r"(api[_-]?key|client_secret|password|private_key|access_token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,}",
    re.IGNORECASE,
)
_DANGEROUS_PATTERN = re.compile(
    r"\b(subprocess\.|os\.system\(|eval\(|exec\(|pip\s+install|__import__)\b",
    re.IGNORECASE,
)


@dataclass
class ImportAuditFinding:
    code: str
    severity: str
    message: str
    path: str | None = None


@dataclass
class ProductSkillImportReport:
    ok: bool
    skill_id: str | None = None
    version: str | None = None
    checksum_sha256: str | None = None
    findings: list[ImportAuditFinding] = field(default_factory=list)
    manifest: ProductSkillManifest | None = None

    def add(self, code: str, message: str, *, severity: str = "error", path: str | None = None) -> None:
        self.findings.append(
            ImportAuditFinding(code=code, severity=severity, message=message, path=path)
        )
        if severity == "error":
            self.ok = False


class ProductSkillImporter:
    """Validate package tree or ZIP. Never executes package scripts."""

    def import_directory(self, root: Path, *, expected_skill_id: str | None = None) -> ProductSkillImportReport:
        report = ProductSkillImportReport(ok=True)
        root = root.resolve()
        if not root.is_dir():
            report.add("not_a_directory", "Package root must be a directory")
            return report

        for path in root.rglob("*"):
            try:
                rel = path.relative_to(root).as_posix()
            except ValueError:
                report.add("path_traversal", "Path outside package root", path=str(path))
                continue
            if self._is_junk(rel):
                continue
            if ".." in PurePosixPath(rel).parts:
                report.add("path_traversal", "Path traversal denied", path=rel)
                continue
            if path.is_symlink():
                report.add("symlink_forbidden", "Symlinks are not allowed", path=rel)
                continue
            if not path.is_file():
                continue
            name = path.name.lower()
            if name in _FORBIDDEN_NAMES or path.suffix.lower() in _FORBIDDEN_SUFFIXES:
                report.add("forbidden_file", f"Forbidden file type: {name}", path=rel)
                continue
            suffix = path.suffix.lower()
            if suffix in {".py", ".js"}:
                # Scripts may exist as reference — never executable in runtime
                report.add(
                    "script_reference_only",
                    "Executable script classified as reference-only; not runnable",
                    severity="warning",
                    path=rel,
                )
            if suffix in {".py", ".js", ".md", ".txt", ".json", ".yaml", ".yml", ".env", ".toml"}:
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    text = ""
                if suffix in {".py", ".js"} and _DANGEROUS_PATTERN.search(text):
                    report.add(
                        "dangerous_executable",
                        "Dangerous executable patterns blocked for commercial runtime",
                        path=rel,
                    )
                if _SECRET_PATTERN.search(text):
                    report.add("secret_detected", "Possible secret material in package", path=rel)

        checksum = self._dir_checksum(root)
        report.checksum_sha256 = checksum

        manifest_path = root / "manifest.json"
        if manifest_path.is_file():
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest = ProductSkillManifest.model_validate(data)
                report.manifest = manifest
                report.skill_id = manifest.skill_id
                report.version = manifest.version
            except Exception as exc:  # noqa: BLE001
                report.add("invalid_manifest", f"Invalid manifest.json: {type(exc).__name__}")
        elif expected_skill_id:
            builtin = get_builtin_manifest(expected_skill_id)
            if builtin is None:
                report.add("missing_manifest", "No manifest.json and unknown skill_id")
            else:
                report.manifest = builtin.model_copy(update={"checksum_sha256": checksum})
                report.skill_id = builtin.skill_id
                report.version = builtin.version
        else:
            report.add("missing_manifest", "manifest.json required unless seeding builtin")

        if report.manifest and expected_skill_id and report.manifest.skill_id != expected_skill_id:
            report.add(
                "skill_id_mismatch",
                f"Expected {expected_skill_id}, got {report.manifest.skill_id}",
            )
        return report

    def import_zip(self, zip_path: Path, extract_to: Path) -> ProductSkillImportReport:
        report = ProductSkillImportReport(ok=True)
        zip_path = zip_path.resolve()
        extract_to = extract_to.resolve()
        extract_to.mkdir(parents=True, exist_ok=True)
        if not zipfile.is_zipfile(zip_path):
            report.add("not_a_zip", "File is not a ZIP archive")
            return report
        with zipfile.ZipFile(zip_path, "r") as zf:
            for info in zf.infolist():
                name = info.filename.replace("\\", "/")
                pure = PurePosixPath(name)
                if (
                    name.startswith("/")
                    or name.startswith("\\")
                    or ".." in pure.parts
                    or pure.is_absolute()
                    or re.match(r"^[A-Za-z]:", name)
                    or name.startswith("//")
                    or name.startswith("\\\\")
                ):
                    report.add("path_traversal", "ZIP path traversal denied", path=name)
                    return report
                if name.endswith("/") or "__MACOSX" in name or name.endswith(".DS_Store"):
                    continue
                # Unix symlink: S_IFLNK = 0o120000 in high 16 bits of external_attr
                mode = (info.external_attr >> 16) & 0o170000
                if mode == 0o120000:
                    report.add(
                        "symlink_forbidden",
                        "ZIP symlink members are not allowed",
                        path=name,
                    )
                    return report
                target = (extract_to / name).resolve()
                try:
                    target.relative_to(extract_to)
                except ValueError:
                    report.add("path_traversal", "ZIP extract escape denied", path=name)
                    return report
            if not report.ok:
                return report
            # Extract member-by-member; never create symlinks
            for info in zf.infolist():
                name = info.filename.replace("\\", "/")
                if name.endswith("/") or "__MACOSX" in name or name.endswith(".DS_Store"):
                    continue
                mode = (info.external_attr >> 16) & 0o170000
                if mode == 0o120000:
                    continue
                target = (extract_to / name).resolve()
                try:
                    target.relative_to(extract_to)
                except ValueError:
                    report.add("path_traversal", "ZIP extract escape denied", path=name)
                    return report
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info, "r") as src, open(target, "wb") as dst:
                    dst.write(src.read())
        # Prefer nested skill root if single top-level dir
        children = [p for p in extract_to.iterdir() if p.name not in {"__MACOSX"}]
        root = children[0] if len(children) == 1 and children[0].is_dir() else extract_to
        return self.import_directory(root)

    def seed_builtins(self) -> list[ProductSkillImportReport]:
        out: list[ProductSkillImportReport] = []
        for manifest in BUILTIN_PRODUCT_SKILLS:
            root = Path(__file__).resolve().parents[2] / "packages" / "product_skills" / manifest.skill_id / manifest.version
            root.mkdir(parents=True, exist_ok=True)
            manifest_path = root / "manifest.json"
            # Do not rewrite curated packages on every request — write once if missing.
            if not manifest_path.is_file():
                payload = manifest.model_dump(mode="json")
                manifest_path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            report = self.import_directory(root, expected_skill_id=manifest.skill_id)
            if report.manifest and report.checksum_sha256:
                report.manifest = report.manifest.model_copy(
                    update={"checksum_sha256": report.checksum_sha256}
                )
            out.append(report)
        return out

    def _is_junk(self, rel: str) -> bool:
        parts = PurePosixPath(rel).parts
        if "__MACOSX" in parts or ".DS_Store" in parts:
            return True
        return any(p.startswith("._") for p in parts)

    def _dir_checksum(self, root: Path) -> str:
        h = hashlib.sha256()
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                continue
            if not path.is_file() or self._is_junk(path.relative_to(root).as_posix()):
                continue
            h.update(path.relative_to(root).as_posix().encode("utf-8"))
            h.update(path.read_bytes())
        return h.hexdigest()
