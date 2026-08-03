#!/usr/bin/env python3
"""REPO-SNAPSHOT-01 — build sanitized mirror for marketsynth-ai-context."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

SRC = Path(r"C:\Users\User\.cursor\projects\c-Users\botfazer")
DST = Path(r"C:\Users\User\.cursor\projects\marketsynth-ai-context-mirror")
REMOTE = "https://github.com/prizrak1234/marketsynth-ai-context.git"

EXCLUDE_DIR_NAMES = {
    ".git",
    ".venv",
    "node_modules",
    ".next",
    "dist",
    "build",
    "coverage",
    "tmp",
    "logs",
    ".cache",
    ".vscode",
    ".idea",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    "playwright-report",
    "test-results",
    "e2e-artifacts",
    "backups",
    "botfazer_backups",
    "generated_visuals",
    "reference_visuals",
    "agent-transcripts",
    "agent-tools",
}

EXCLUDE_DIR_PREFIXES = (".tmp_", ".tmp")

EXCLUDE_FILE_SUFFIXES = (
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".pyc",
    ".pyo",
    ".log",
    ".dump",
    ".sql",
    ".db",
)

EXCLUDE_FILE_NAMES = {
    "service-account.json",
    ".env",
    ".DS_Store",
    "Thumbs.db",
}

# Keep only *.example env templates
ENV_ALLOW = {".env.example"}

REDACT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"AIza[0-9A-Za-z\-_]{20,}"), "AIzaSy_REDACTED"),
    (re.compile(r"sb_secret_[A-Za-z0-9_\-]{8,}"), "sb_secret_REDACTED"),
    (re.compile(r"ghp_[A-Za-z0-9]{20,}"), "ghp_REDACTED"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "github_pat_REDACTED"),
    (re.compile(r"xoxb-[0-9A-Za-z\-]{10,}"), "xoxb-REDACTED"),
    (re.compile(r"sk-proj-[A-Za-z0-9_\-]{20,}"), "sk-proj-REDACTED"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "sk-REDACTED"),
    (
        re.compile(
            r"-----BEGIN (?:RSA |OPENSSH |EC |OPENPGP )?PRIVATE KEY-----[\s\S]*?"
            r"-----END (?:RSA |OPENSSH |EC |OPENPGP )?PRIVATE KEY-----"
        ),
        "-----BEGIN PRIVATE KEY-----
<REDACTED>
-----END PRIVATE KEY-----",
    ),
    # Telegram-looking tokens in archived docs/workflows
    (re.compile(r"\b\d{8,12}:[A-Za-z0-9_\-]{30,}\b"), "<TELEGRAM_BOT_TOKEN_REDACTED>"),
]

TEXT_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".mdc",
    ".txt",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".cfg",
    ".css",
    ".scss",
    ".html",
    ".svg",
    ".env",
    ".example",
    ".sh",
    ".ps1",
    ".sql",
    ".csv",
    ".xml",
    ".graphql",
    ".gitignore",
    ".dockerignore",
    ".editorconfig",
}


def should_skip_dir(name: str) -> bool:
    if name in EXCLUDE_DIR_NAMES:
        return True
    if name.startswith(EXCLUDE_DIR_PREFIXES):
        return True
    return False


def should_skip_file(path: Path) -> bool:
    name = path.name
    if name in EXCLUDE_FILE_NAMES:
        return True
    if name.startswith(".env") and name not in ENV_ALLOW and not name.endswith(".example"):
        return True
    if name.endswith(EXCLUDE_FILE_SUFFIXES):
        # allow fixture .db under tests/fixtures if any — still skip binary dbs for safety
        return True
    if name == "uv.lock":
        return False  # include lockfile in mirror even if source gitignored
    return False


def redact_text(text: str) -> tuple[str, int]:
    hits = 0
    out = text
    for pattern, repl in REDACT_PATTERNS:
        out, n = pattern.subn(repl, out)
        hits += n
    return out, hits


def copy_tree() -> tuple[int, int, int]:
    if DST.exists():
        # Keep .git if already a clone
        for child in list(DST.iterdir()):
            if child.name == ".git":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    else:
        DST.mkdir(parents=True)

    files_copied = 0
    files_redacted = 0
    redact_hits = 0

    for src_path in SRC.rglob("*"):
        rel = src_path.relative_to(SRC)
        parts = rel.parts
        # Skip if any ancestor directory is excluded
        if any(should_skip_dir(part) for part in parts[:-1]):
            continue
        if src_path.is_dir():
            if should_skip_dir(src_path.name):
                continue
            continue
        if should_skip_file(src_path):
            continue

        dest_path = DST / rel
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        suffix = src_path.suffix.lower()
        is_text = (
            suffix in TEXT_SUFFIXES
            or src_path.name in {".gitignore", ".gitattributes", "Dockerfile", "Makefile", "LICENSE"}
            or src_path.name.endswith(".example")
        )
        if is_text:
            try:
                raw = src_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                shutil.copy2(src_path, dest_path)
                files_copied += 1
                continue
            cleaned, hits = redact_text(raw)
            dest_path.write_text(cleaned, encoding="utf-8", newline="\n")
            files_copied += 1
            if hits:
                files_redacted += 1
                redact_hits += hits
        else:
            shutil.copy2(src_path, dest_path)
            files_copied += 1

    return files_copied, files_redacted, redact_hits


def write_mirror_gitignore() -> None:
    gitignore = (SRC / ".gitignore").read_text(encoding="utf-8")
    (DST / ".gitignore").write_text(gitignore, encoding="utf-8", newline="\n")


def ensure_env_examples() -> None:
    root_example = DST / ".env.example"
    if not root_example.exists():
        raise SystemExit("missing .env.example in mirror")
    text = root_example.read_text(encoding="utf-8")
    extras = []
    for key in (
        "JWT_SECRET=",
        "SESSION_SECRET=",
        "SUPABASE_URL=",
        "SUPABASE_ANON_KEY=",
        "SUPABASE_SERVICE_ROLE_KEY=",
    ):
        if key.split("=")[0] not in text:
            extras.append(key)
    if extras:
        text = text.rstrip() + "\n\n# --- Optional / future integrations (empty placeholders) ---\n"
        text += "\n".join(extras) + "\n"
        root_example.write_text(text, encoding="utf-8", newline="\n")


def scan_mirror_for_leaks() -> list[str]:
    """Return findings as 'path: pattern' without secret values."""
    findings: list[str] = []
    checks = [
        ("AIza_live", re.compile(r"AIzaSy(?!_REDACTED)[0-9A-Za-z\-_]{20,}")),
        ("sb_secret_live", re.compile(r"sb_secret_(?!REDACTED)[A-Za-z0-9_\-]{8,}")),
        ("ghp_live", re.compile(r"ghp_[A-Za-z0-9]{36,}")),
        ("sk_live", re.compile(r"sk-(?!REDACTED|your-key-here|proj-REDACTED)[A-Za-z0-9]{24,}")),
        ("private_key_block", re.compile(r"BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----\s*\n(?!<REDACTED>)")),
    ]
    for path in DST.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {".gitignore"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for label, pattern in checks:
            if pattern.search(text):
                findings.append(f"{path.relative_to(DST).as_posix()}: {label}")
    return findings


def main() -> int:
    print("SRC", SRC)
    print("DST", DST)
    if not (DST / ".git").exists():
        print("Cloning remote…")
        DST.parent.mkdir(parents=True, exist_ok=True)
        if DST.exists():
            shutil.rmtree(DST)
        subprocess.check_call(["git", "clone", REMOTE, str(DST)])
    else:
        print("Using existing clone")
        subprocess.check_call(["git", "-C", str(DST), "fetch", "origin"], cwd=DST)
        subprocess.check_call(["git", "-C", str(DST), "checkout", "main"], cwd=DST)
        subprocess.call(["git", "-C", str(DST), "pull", "--ff-only", "origin", "main"], cwd=DST)

    copied, redacted_files, hits = copy_tree()
    write_mirror_gitignore()
    ensure_env_examples()
    # Always overwrite mirror README banner for context-repo purpose
    banner = (
        "# Marketsynth AI Context (sanitized mirror)\n\n"
        "Architecture / SoT / structure backup for recovery. **Not** a production deploy repo.\n\n"
        "Secrets are excluded or replaced with `<REDACTED>` / empty placeholders. "
        "Copy `.env.example` → `.env` and fill locally.\n\n"
        "Source snapshot task: **REPO-SNAPSHOT-01**.\n"
    )
    readme = DST / "README.md"
    if readme.exists():
        body = readme.read_text(encoding="utf-8")
        if "REPO-SNAPSHOT-01" not in body:
            readme.write_text(banner + "\n---\n\n" + body, encoding="utf-8", newline="\n")
    else:
        readme.write_text(banner, encoding="utf-8", newline="\n")

    findings = scan_mirror_for_leaks()
    print(f"copied={copied} redacted_files={redacted_files} redact_hits={hits}")
    if findings:
        print("LEAK_FINDINGS")
        for f in findings[:50]:
            print(f)
        print(f"total_findings={len(findings)}")
        return 2
    print("LEAK_SCAN_CLEAN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
