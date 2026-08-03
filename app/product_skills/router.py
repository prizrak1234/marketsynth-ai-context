"""Compact skill router — never loads full skill corpus into prompts."""

from __future__ import annotations

from dataclasses import dataclass

from app.product_skills.catalog import BUILTIN_PRODUCT_SKILLS
from app.product_skills.secret_binding import all_aliases_configured
from app.product_skills.tools_avito import avito_configured
from app.schemas.contracts import (
    ProductSkillInstallStatus,
    ProductSkillManifest,
)


@dataclass(frozen=True)
class SkillRouteDecision:
    manifest: ProductSkillManifest | None
    mode: str  # explicit | automatic | none
    reason: str
    available_index: list[dict[str, str]]


class ProductSkillRouter:
    def __init__(self, *, install_status: dict[str, ProductSkillInstallStatus] | None = None):
        self._install_status = install_status or {}

    def compact_index(self) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        for m in BUILTIN_PRODUCT_SKILLS:
            status = self._effective_status(m)
            if status in {
                ProductSkillInstallStatus.DISABLED,
                ProductSkillInstallStatus.BLOCKED,
                ProductSkillInstallStatus.SUPERSEDED,
            }:
                continue
            if not m.enabled:
                continue
            configured = all_aliases_configured(list(m.required_secret_aliases))
            if m.skill_id == "marketsynth.avito":
                configured = avito_configured()
            if (
                status == ProductSkillInstallStatus.INSTALLED_UNCONFIGURED
                or not configured
            ) and m.required_secret_aliases:
                # Unconfigured integrations excluded from automatic availability
                availability = "unconfigured"
            else:
                availability = "available"
            items.append(
                {
                    "skill_id": m.skill_id,
                    "description": m.description[:240],
                    "triggers": ",".join(m.triggers),
                    "input": ",".join(m.accepted_input_types),
                    "output": ",".join(m.output_types),
                    "availability": availability,
                    "version": m.version,
                }
            )
        return items

    def route(
        self,
        *,
        skill_id: str | None = None,
        trigger: str | None = None,
        input_type: str | None = None,
        explicit: bool = False,
    ) -> SkillRouteDecision:
        index = self.compact_index()
        if explicit or skill_id:
            if not skill_id:
                return SkillRouteDecision(None, "none", "explicit_skill_id_required", index)
            manifest = next((m for m in BUILTIN_PRODUCT_SKILLS if m.skill_id == skill_id), None)
            if manifest is None:
                return SkillRouteDecision(None, "explicit", "skill_not_found", index)
            status = self._effective_status(manifest)
            if status == ProductSkillInstallStatus.DISABLED or not manifest.enabled:
                return SkillRouteDecision(None, "explicit", "skill_disabled", index)
            configured = all_aliases_configured(list(manifest.required_secret_aliases))
            if manifest.skill_id == "marketsynth.avito":
                configured = avito_configured()
            if manifest.required_secret_aliases and not configured:
                return SkillRouteDecision(
                    None, "explicit", "skill_unconfigured", index
                )
            return SkillRouteDecision(
                manifest, "explicit", "explicit_selection", index
            )

        # Automatic: match trigger / input against available configured skills
        trigger_l = (trigger or "").lower().strip()
        for m in BUILTIN_PRODUCT_SKILLS:
            status = self._effective_status(m)
            if status in {
                ProductSkillInstallStatus.DISABLED,
                ProductSkillInstallStatus.BLOCKED,
                ProductSkillInstallStatus.INSTALLED_UNCONFIGURED,
            }:
                continue
            if not m.enabled:
                continue
            if m.required_secret_aliases:
                ready = (
                    avito_configured()
                    if m.skill_id == "marketsynth.avito"
                    else all_aliases_configured(list(m.required_secret_aliases))
                )
                if not ready:
                    continue
            if input_type and input_type not in m.accepted_input_types:
                continue
            if trigger_l and not any(trigger_l == t.lower() or trigger_l in t.lower() for t in m.triggers):
                continue
            if not trigger_l and input_type and input_type in m.accepted_input_types:
                return SkillRouteDecision(
                    m, "automatic", f"input_type:{input_type}", index
                )
            if trigger_l:
                return SkillRouteDecision(
                    m, "automatic", f"trigger:{trigger_l}", index
                )
        return SkillRouteDecision(None, "none", "no_compatible_skill", index)

    def _effective_status(self, manifest: ProductSkillManifest) -> ProductSkillInstallStatus:
        if manifest.skill_id in self._install_status:
            return self._install_status[manifest.skill_id]
        if manifest.skill_id == "marketsynth.avito":
            return (
                ProductSkillInstallStatus.INSTALLED
                if avito_configured()
                else ProductSkillInstallStatus.INSTALLED_UNCONFIGURED
            )
        if manifest.required_secret_aliases and not all_aliases_configured(
            list(manifest.required_secret_aliases)
        ):
            return ProductSkillInstallStatus.INSTALLED_UNCONFIGURED
        return ProductSkillInstallStatus.INSTALLED
