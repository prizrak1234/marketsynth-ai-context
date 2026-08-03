"""CWF.1 owner golden-path smoke — API + DB lineage evidence (no new features).

Run: uv run python scripts/cwf1_golden_path_smoke.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from uuid import uuid4

from app.business_idea_validation.output_enrichment import enrich_output_commercial
from app.core.config import get_settings
from app.db.base import utc_now
from app.db.models.business_idea_validation_run import BusinessIdeaValidationRunTable
from app.db.models.user_request import UserRequestTable
from app.db.repositories.business_idea_validation_runs import BusinessIdeaValidationRunRepository
from app.db.session import close_db, get_session_factory, init_db, reset_db_state
from app.schemas.contracts import (
    AnalysisContextCreateDraftRequest,
    AnalysisContextConfirmRequest,
    AnalysisContextEditRequest,
    AnalysisContextState,
    BivResearchTerminalState,
    BusinessIdeaValidationRunRequest,
    BusinessIdeaValidationRunStatus,
    BusinessIdeaValidationVerdictKind,
)
from app.services.analysis_context_service import AnalysisContextService
from app.services.business_idea_validation_service import (
    BusinessIdeaValidationService,
    build_rerun_idempotency_key,
)
from tests.test_cwf_1a_launch_pack_decision import _output
from tests.test_product_01_3a_biv_intake_gate import _seed_confirmed_context, _valid_fields


async def _count_runs(repo: BusinessIdeaValidationRunRepository, owner_id, user_request_id) -> int:
    from sqlalchemy import func, select

    stmt = select(func.count()).select_from(BusinessIdeaValidationRunTable).where(
        BusinessIdeaValidationRunTable.owner_id == owner_id,
        BusinessIdeaValidationRunTable.user_request_id == user_request_id,
    )
    result = await repo._session.execute(stmt)  # noqa: SLF001
    return int(result.scalar_one())


async def main() -> int:
    reset_db_state()
    await init_db(get_settings())
    factory = get_session_factory()
    evidence: dict[str, object] = {"steps": []}

    async with factory() as session:
        owner_id, project_id, confirmed = await _seed_confirmed_context(session)
        request_id = uuid4()
        now = utc_now()
        legacy_output = _output(
            BusinessIdeaValidationVerdictKind.INSUFFICIENT_EVIDENCE,
            research_terminal_state=BivResearchTerminalState.SUCCEEDED_INSUFFICIENT,
            analysis_context_id=confirmed.context_id,
            input_snapshot_hash=confirmed.input_snapshot_hash,
            project_id=project_id,
            run_id=None,
        )
        old_run_id = uuid4()
        session.add(
            UserRequestTable(
                id=request_id,
                owner_id=owner_id,
                tenant_id=owner_id,
                project_id=project_id,
                text=_valid_fields().idea_description,
                normalized_text=_valid_fields().idea_description,
                skill_inputs={"analysis_context_id": str(confirmed.context_id)},
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            BusinessIdeaValidationRunTable(
                id=old_run_id,
                owner_id=owner_id,
                tenant_id=owner_id,
                user_request_id=request_id,
                project_id=project_id,
                investigation_id=uuid4(),
                analysis_context_id=confirmed.context_id,
                input_snapshot_hash=confirmed.input_snapshot_hash,
                idempotency_key="biv-research-smoke-original",
                status=BusinessIdeaValidationRunStatus.SUCCEEDED,
                result_json=legacy_output.model_dump(mode="json"),
                created_at=now,
                updated_at=now,
                finished_at=now,
            )
        )
        await session.commit()

        svc = BusinessIdeaValidationService(session, get_settings())
        repo = BusinessIdeaValidationRunRepository(session)

        # Step 1: legacy hydration → customer_report
        hydration = await svc.get_project_hydration(owner_id, project_id)
        step1_ok = (
            hydration is not None
            and hydration.output.customer_report is not None
            and hydration.run_id == old_run_id
        )
        evidence["steps"].append(
            {
                "step": 1,
                "name": "legacy_hydration_customer_report",
                "pass": step1_ok,
                "old_run_id": str(old_run_id),
                "has_customer_report": hydration.output.customer_report is not None if hydration else False,
            }
        )

        # Step 2: rerun on same user_request_id (lineage)
        new_output = enrich_output_commercial(
            _output(
                BusinessIdeaValidationVerdictKind.REVISE,
                research_terminal_state=BivResearchTerminalState.SUCCEEDED_INSUFFICIENT,
                analysis_context_id=confirmed.context_id,
                input_snapshot_hash=confirmed.input_snapshot_hash,
                project_id=project_id,
            )
        )

        async def fake_skill_run(_self, _inp):
            return new_output

        from app.business_idea_validation import skill as skill_mod

        original_run = skill_mod.BusinessIdeaValidationSkill.run
        skill_mod.BusinessIdeaValidationSkill.run = fake_skill_run  # type: ignore[method-assign]

        rerun_key = build_rerun_idempotency_key(
            confirmed.context_id,
            confirmed.input_snapshot_hash or "a" * 64,
        )
        runs_before = await _count_runs(repo, owner_id, request_id)
        rerun_resp = await svc.run(
            owner_id,
            request_id,
            BusinessIdeaValidationRunRequest(
                idempotency_key=rerun_key,
                analysis_context_id=confirmed.context_id,
                input_snapshot_hash=confirmed.input_snapshot_hash or "a" * 64,
                research_intent=True,
                rerun_intent=True,
            ),
        )
        runs_after = await _count_runs(repo, owner_id, request_id)
        old_preserved = await repo.get_by_id(old_run_id) is not None
        latest = await svc.get_latest(owner_id, request_id)

        step2_ok = (
            rerun_resp.run_id != old_run_id
            and rerun_resp.output is not None
            and rerun_resp.output.customer_report is not None
            and runs_after == runs_before + 1
            and old_preserved
            and latest is not None
            and latest.run_id == rerun_resp.run_id
        )
        evidence["steps"].append(
            {
                "step": 2,
                "name": "rerun_new_run_customer_report",
                "pass": step2_ok,
                "old_run_id": str(old_run_id),
                "new_run_id": str(rerun_resp.run_id),
                "runs_before": runs_before,
                "runs_after": runs_after,
                "old_run_preserved": old_preserved,
                "same_user_request_id": str(request_id),
            }
        )

        # Double-click idempotency
        dup = await svc.run(
            owner_id,
            request_id,
            BusinessIdeaValidationRunRequest(
                idempotency_key=rerun_key,
                analysis_context_id=confirmed.context_id,
                input_snapshot_hash=confirmed.input_snapshot_hash or "a" * 64,
                research_intent=True,
                rerun_intent=True,
            ),
        )
        runs_after_dup = await _count_runs(repo, owner_id, request_id)
        step2b_ok = dup.run_id == rerun_resp.run_id and runs_after_dup == runs_after
        evidence["steps"].append(
            {
                "step": "2b",
                "name": "rerun_idempotent_no_duplicate",
                "pass": step2b_ok,
                "duplicate_runs": runs_after_dup - runs_after,
            }
        )

        skill_mod.BusinessIdeaValidationSkill.run = original_run  # type: ignore[method-assign]

        # Step 3: clarify → edit → confirm → rerun
        ctx_svc = AnalysisContextService(session, get_settings())
        edited = await ctx_svc.edit(
            owner_id,
            project_id,
            confirmed.context_id,
            AnalysisContextEditRequest(
                **_valid_fields(analysis_goal="Уточнённая цель smoke-теста").model_dump()
            ),
        )
        reconfirmed = await ctx_svc.confirm(
            owner_id,
            project_id,
            edited.context_id,
            AnalysisContextConfirmRequest(input_snapshot_hash=edited.input_snapshot_hash),
        )
        clarify_key = build_rerun_idempotency_key(
            reconfirmed.context_id,
            reconfirmed.input_snapshot_hash or "a" * 64,
        )
        skill_mod.BusinessIdeaValidationSkill.run = fake_skill_run  # type: ignore[method-assign]
        clarify_resp = await svc.run(
            owner_id,
            request_id,
            BusinessIdeaValidationRunRequest(
                idempotency_key=clarify_key,
                analysis_context_id=reconfirmed.context_id,
                input_snapshot_hash=reconfirmed.input_snapshot_hash or "a" * 64,
                research_intent=True,
                rerun_intent=True,
            ),
        )
        skill_mod.BusinessIdeaValidationSkill.run = original_run  # type: ignore[method-assign]

        step3_ok = (
            clarify_resp.run_id != rerun_resp.run_id
            and reconfirmed.input_snapshot_hash != confirmed.input_snapshot_hash
            and clarify_resp.output is not None
            and clarify_resp.output.customer_report is not None
        )
        evidence["steps"].append(
            {
                "step": 3,
                "name": "clarify_edit_rerun",
                "pass": step3_ok,
                "old_snapshot": confirmed.input_snapshot_hash,
                "new_snapshot": reconfirmed.input_snapshot_hash,
                "clarify_run_id": str(clarify_resp.run_id),
            }
        )

        # Step 4: refresh simulation — project hydration returns latest
        refresh = await svc.get_project_hydration(
            owner_id,
            project_id,
            analysis_context_id=reconfirmed.context_id,
            input_snapshot_hash=reconfirmed.input_snapshot_hash,
        )
        step4_ok = (
            refresh is not None
            and refresh.run_id == clarify_resp.run_id
            and refresh.output.customer_report is not None
        )
        evidence["steps"].append(
            {
                "step": 4,
                "name": "refresh_persists_latest_report",
                "pass": step4_ok,
                "hydrated_run_id": str(refresh.run_id) if refresh else None,
            }
        )

        evidence["all_pass"] = all(s["pass"] for s in evidence["steps"] if isinstance(s, dict))
        evidence["lineage_note"] = (
            "Same user_request_id links multiple run rows; each run has unique run_id; "
            "old runs remain in business_idea_validation_runs; get_latest returns newest."
        )

    await close_db()
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if evidence.get("all_pass") else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
