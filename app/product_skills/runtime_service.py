"""Product Skill Runtime service — select, persist SkillRun, execute safely."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_payload, sanitize_text
from app.db.base import utc_now
from app.db.models.product_skills import ProductSkillInstallationTable, ProductSkillRunTable
from app.product_skills.catalog import BUILTIN_PRODUCT_SKILLS, package_root_for
from app.product_skills.importer import ProductSkillImporter
from app.product_skills.router import ProductSkillRouter
from app.product_skills.secret_binding import all_aliases_configured
from app.product_skills.tools_avito import (
    avito_account_read,
    avito_analytics_read,
    avito_configured,
    avito_credentials_present,
    avito_live_ready,
)
from app.product_skills.tools_wordstat import wordstat_expand, wordstat_frequency, wordstat_related
from app.schemas.contracts import (
    ProductSkillIndexItem,
    ProductSkillInstallStatus,
    ProductSkillRunCreate,
    ProductSkillRunRead,
    ProductSkillRunStatus,
    ProductSkillType,
    ProductSkillWorkspaceState,
)
from app.services.projects_service import ProjectService
from app.services.transaction import transactional


def _run_to_read(row: ProductSkillRunTable) -> ProductSkillRunRead:
    return ProductSkillRunRead(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        skill_id=row.skill_id,
        skill_version=row.skill_version,
        status=ProductSkillRunStatus(row.status),
        selection_mode=row.selection_mode,
        selection_reason=row.selection_reason,
        input_type=row.input_type,
        input_ref=dict(row.input_ref or {}),
        result_ref=dict(row.result_ref or {}),
        evidence=dict(row.evidence or {}),
        safe_error=row.safe_error,
        error_code=row.error_code,
        idempotency_key=row.idempotency_key,
        correlation_id=row.correlation_id,
        started_at=row.started_at,
        finished_at=row.finished_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class ProductSkillRuntimeService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._projects = ProjectService(session)
        self._importer = ProductSkillImporter()

    async def ensure_seeded_for_owner(self, owner_id: UUID) -> None:
        reports = self._importer.seed_builtins()
        for report in reports:
            if not report.ok or report.manifest is None:
                continue
            m = report.manifest
            existing = await self._get_install(owner_id, m.skill_id)
            configured = all_aliases_configured(list(m.required_secret_aliases))
            if m.skill_id == "marketsynth.avito":
                # Credentials may exist, but live ports are disabled — stay unconfigured/not Available.
                configured = avito_configured()
                status = (
                    ProductSkillInstallStatus.INSTALLED
                    if configured
                    else ProductSkillInstallStatus.INSTALLED_UNCONFIGURED
                )
            elif configured or not m.required_secret_aliases:
                status = ProductSkillInstallStatus.INSTALLED
            else:
                status = ProductSkillInstallStatus.INSTALLED_UNCONFIGURED
            last_error = None
            if m.skill_id == "marketsynth.avito" and avito_credentials_present() and not avito_live_ready():
                last_error = "Avito live API not enabled yet"
            if existing is None:
                row = ProductSkillInstallationTable(
                    owner_id=owner_id,
                    skill_id=m.skill_id,
                    skill_version=m.version,
                    install_status=status.value,
                    enabled=True,
                    checksum_sha256=report.checksum_sha256,
                    configured=configured,
                    last_error=last_error,
                    provenance=m.provenance,
                )
                async with transactional(self._session):
                    self._session.add(row)
            else:
                existing.skill_version = m.version
                existing.checksum_sha256 = report.checksum_sha256 or existing.checksum_sha256
                existing.configured = configured
                existing.install_status = status.value
                existing.last_error = last_error
                existing.updated_at = utc_now()
                async with transactional(self._session):
                    self._session.add(existing)

    async def list_skills(self, owner_id: UUID) -> list[ProductSkillIndexItem]:
        await self.ensure_seeded_for_owner(owner_id)
        installs = {
            row.skill_id: row
            for row in (
                await self._session.execute(
                    select(ProductSkillInstallationTable).where(
                        ProductSkillInstallationTable.owner_id == owner_id
                    )
                )
            ).scalars().all()
        }
        items: list[ProductSkillIndexItem] = []
        for m in BUILTIN_PRODUCT_SKILLS:
            inst = installs.get(m.skill_id)
            configured = all_aliases_configured(list(m.required_secret_aliases))
            if m.skill_id == "marketsynth.avito":
                configured = avito_configured()
            status = ProductSkillInstallStatus(
                inst.install_status if inst else ProductSkillInstallStatus.INSTALLED.value
            )
            if m.skill_id == "marketsynth.avito" and not avito_live_ready():
                status = ProductSkillInstallStatus.INSTALLED_UNCONFIGURED
            elif m.required_secret_aliases and not configured:
                status = ProductSkillInstallStatus.INSTALLED_UNCONFIGURED
            last = await self._last_run(owner_id, m.skill_id)
            safe_error = inst.last_error if inst else None
            if m.skill_id == "marketsynth.avito" and not avito_live_ready():
                safe_error = safe_error or "Avito live API not enabled yet"
            items.append(
                ProductSkillIndexItem(
                    skill_id=m.skill_id,
                    name=m.name,
                    version=m.version,
                    description=m.description,
                    type=m.type,
                    triggers=list(m.triggers),
                    accepted_input_types=list(m.accepted_input_types),
                    output_types=list(m.output_types),
                    install_status=status,
                    configured=configured,
                    enabled=bool(inst.enabled) if inst else True,
                    # Do not expose env-style secret alias names on the product index.
                    required_secret_aliases=[],
                    permissions_summary=self._permissions_summary(m),
                    last_run_status=last.status if last else None,
                    last_run_at=last.finished_at or last.created_at if last else None,
                    safe_error=safe_error,
                )
            )
        return items

    async def workspace(self, owner_id: UUID) -> ProductSkillWorkspaceState:
        skills = await self.list_skills(owner_id)
        return ProductSkillWorkspaceState(skills=skills, next_action="browse")

    async def get_run(
        self,
        owner_id: UUID,
        project_id: UUID,
        run_id: UUID,
    ) -> ProductSkillRunRead | None:
        row = await self._session.get(ProductSkillRunTable, run_id)
        if row is None or row.owner_id != owner_id or row.project_id != project_id:
            return None
        return _run_to_read(row)

    async def get_run_by_idempotency(
        self,
        owner_id: UUID,
        project_id: UUID,
        idempotency_key: str,
    ) -> ProductSkillRunRead | None:
        row = await self._get_by_idempotency(owner_id, project_id, idempotency_key)
        return _run_to_read(row) if row else None

    async def execute(
        self,
        owner_id: UUID,
        project_id: UUID,
        body: ProductSkillRunCreate,
    ) -> ProductSkillRunRead | None:
        project = await self._projects.get_by_id(project_id)
        if project is None or project.owner_id != owner_id:
            return None
        await self.ensure_seeded_for_owner(owner_id)

        cleaned_input = sanitize_payload(body.input_ref) or {}
        idem = body.idempotency_key
        if idem:
            existing = await self._get_by_idempotency(owner_id, project_id, idem)
            if existing is not None:
                return _run_to_read(existing)

        install_map = {
            i.skill_id: ProductSkillInstallStatus(i.install_status)
            for i in (
                await self._session.execute(
                    select(ProductSkillInstallationTable).where(
                        ProductSkillInstallationTable.owner_id == owner_id
                    )
                )
            ).scalars().all()
        }
        router = ProductSkillRouter(install_status=install_map)
        decision = router.route(
            skill_id=body.skill_id,
            trigger=body.trigger,
            input_type=body.input_type,
            explicit=body.explicit or bool(body.skill_id),
        )
        if decision.manifest is None:
            raise InvalidStateError(decision.reason)

        manifest = decision.manifest
        run = ProductSkillRunTable(
            owner_id=owner_id,
            project_id=project_id,
            skill_id=manifest.skill_id,
            skill_version=manifest.version,
            status=ProductSkillRunStatus.RUNNING.value,
            selection_mode=decision.mode,
            selection_reason=decision.reason,
            input_type=body.input_type,
            input_ref=cleaned_input,
            result_ref={},
            evidence={"router_index_size": len(decision.available_index)},
            idempotency_key=idem,
            correlation_id=str(uuid4()),
            started_at=utc_now(),
        )
        async with transactional(self._session):
            self._session.add(run)
            await self._session.flush()

        try:
            result, evidence = await self._dispatch(manifest, cleaned_input)
            async with transactional(self._session):
                run.status = ProductSkillRunStatus.SUCCEEDED.value
                run.result_ref = result
                run.evidence = {**(run.evidence or {}), **evidence}
                run.finished_at = utc_now()
                run.updated_at = utc_now()
                self._session.add(run)
        except InvalidStateError as exc:
            async with transactional(self._session):
                run.status = ProductSkillRunStatus.FAILED.value
                run.error_code = str(exc).split(":", 1)[0][:64]
                run.safe_error = str(exc).split(":", 1)[0][:240]
                run.finished_at = utc_now()
                run.updated_at = utc_now()
                self._session.add(run)
        except Exception:  # noqa: BLE001
            async with transactional(self._session):
                run.status = ProductSkillRunStatus.FAILED.value
                run.error_code = "skill_execution_failure"
                run.safe_error = "Skill execution failed"
                run.finished_at = utc_now()
                run.updated_at = utc_now()
                self._session.add(run)

        refreshed = await self._session.get(ProductSkillRunTable, run.id)
        return _run_to_read(refreshed or run)

    async def _dispatch(
        self,
        manifest: Any,
        input_ref: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if manifest.type == ProductSkillType.INSTRUCTION:
            return self._run_instruction(manifest, input_ref)
        if manifest.skill_id == "marketsynth.xmlriver.wordstat":
            tool = str(input_ref.get("tool") or "wordstat.frequency")
            query = sanitize_text(str(input_ref.get("query") or ""))
            if not query:
                raise InvalidStateError("missing_query")
            if tool == "wordstat.frequency":
                data = wordstat_frequency(manifest, query)
            elif tool == "wordstat.expand":
                data = wordstat_expand(manifest, query)
            elif tool == "wordstat.related":
                data = wordstat_related(manifest, query)
            else:
                raise InvalidStateError("permission_denied: tool")
            return data, {"tool": tool, "external_action": "read"}
        if manifest.skill_id == "marketsynth.avito":
            tool = str(input_ref.get("tool") or "avito.analytics.read")
            if tool == "avito.analytics.read":
                data = avito_analytics_read(manifest)
            elif tool == "avito.account.read":
                data = avito_account_read(manifest)
            else:
                raise InvalidStateError("avito_write_disabled")
            return data, {"tool": tool}
        raise InvalidStateError("unsupported_skill_type")

    def _run_instruction(
        self,
        manifest: Any,
        input_ref: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Load versioned instructions; generation itself is performed by Content Director adapter."""
        root = package_root_for(manifest.skill_id, manifest.version)
        skill_md = root / "SKILL.md"
        system_prompt = root / "resources" / "system_prompt.md"
        instructions = ""
        if skill_md.is_file():
            instructions = skill_md.read_text(encoding="utf-8")[:12000]
        system = ""
        if system_prompt.is_file():
            system = system_prompt.read_text(encoding="utf-8")[:20000]
        ready_flag = (
            "ready_for_visual_director"
            if manifest.skill_id == "marketsynth.visual_generation"
            else "ready_for_content_director"
        )
        return (
            {
                "skill_id": manifest.skill_id,
                "skill_version": manifest.version,
                "instruction_loaded": bool(instructions),
                "system_prompt_loaded": bool(system),
                "input_ref": input_ref,
                ready_flag: True,
            },
            {
                "package_root": str(root.as_posix()),
                "entrypoint": manifest.instruction_entrypoint,
                "instruction_chars": len(instructions),
                "system_prompt_chars": len(system),
            },
        )

    def load_copywriter_prompts(self) -> dict[str, str]:
        root = package_root_for("marketsynth.copywriter", "1.0.0")
        skill_md = (root / "SKILL.md").read_text(encoding="utf-8") if (root / "SKILL.md").is_file() else ""
        system = (
            (root / "resources" / "system_prompt.md").read_text(encoding="utf-8")
            if (root / "resources" / "system_prompt.md").is_file()
            else ""
        )
        return {"skill_md": skill_md, "system_prompt": system}

    async def _get_install(
        self, owner_id: UUID, skill_id: str
    ) -> ProductSkillInstallationTable | None:
        result = await self._session.execute(
            select(ProductSkillInstallationTable).where(
                ProductSkillInstallationTable.owner_id == owner_id,
                ProductSkillInstallationTable.skill_id == skill_id,
            )
        )
        return result.scalar_one_or_none()

    async def _last_run(self, owner_id: UUID, skill_id: str) -> ProductSkillRunTable | None:
        result = await self._session.execute(
            select(ProductSkillRunTable)
            .where(
                ProductSkillRunTable.owner_id == owner_id,
                ProductSkillRunTable.skill_id == skill_id,
            )
            .order_by(ProductSkillRunTable.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_by_idempotency(
        self, owner_id: UUID, project_id: UUID, key: str
    ) -> ProductSkillRunTable | None:
        result = await self._session.execute(
            select(ProductSkillRunTable).where(
                ProductSkillRunTable.owner_id == owner_id,
                ProductSkillRunTable.project_id == project_id,
                ProductSkillRunTable.idempotency_key == key,
            )
        )
        return result.scalar_one_or_none()

    def _permissions_summary(self, manifest: Any) -> str:
        tools = ",".join(manifest.allowed_tools) or "none"
        hosts = ",".join(manifest.allowed_network_hosts) or "none"
        return f"tools={tools}; network={hosts}; secrets={len(manifest.required_secret_aliases)}"
