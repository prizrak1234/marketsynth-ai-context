"""CLI entrypoint for Skill package validation (SKILL-01.2)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.skills.package_validator import validate_skill_package
from app.skills.validation_contracts import SkillValidationMode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a Marketsynth Skill package (read-only).",
    )
    parser.add_argument("package_path", type=Path, help="Path to Skill package root")
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in SkillValidationMode],
        default=SkillValidationMode.CANDIDATE.value,
    )
    parser.add_argument("--json", action="store_true", help="Emit full validation report as JSON")
    args = parser.parse_args(argv)

    report = validate_skill_package(
        args.package_path,
        mode=SkillValidationMode(args.mode),
    )

    if args.json:
        print(json.dumps(report.model_dump(mode="json"), indent=2, default=str))
    else:
        print(f"valid: {report.valid}")
        print(f"skill_id: {report.skill_id}")
        print(f"version: {report.skill_version}")
        print(f"status: {report.status}")
        print(f"hash: {report.package_hash}")
        if report.errors:
            print("errors:")
            for issue in report.errors:
                print(f"  - [{issue.code}] {issue.message}")
        if report.warnings:
            print("warnings:")
            for issue in report.warnings:
                print(f"  - [{issue.code}] {issue.message}")

    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
