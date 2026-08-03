"""Phase H2.3–H2.5 — durable knowledge, retrieval, UserRequest skill attachment."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge_foundation.ingestion import ingest_approved_content_pack
from app.knowledge_foundation.retrieval_adapter import (
    RETRIEVAL_POLICY_VERSION,
    KnowledgeRetrievalAdapter,
    compute_snapshot_hash,
)
from app.knowledge_foundation.snapshot_service import KnowledgeSnapshotService
from app.knowledge_foundation.store import KnowledgeStoreService, content_hash
from app.schemas.contracts import (
    KnowledgeAuthority,
    KnowledgeContentFormat,
    KnowledgeDomain,
    KnowledgeItemStatus,
    KnowledgeRetrievalRequest,
    KnowledgeTenantScope,
    KnowledgeType,
    SpecialistSkillCode,
    UserRequestExecutionReadiness,
    UserRequestStatus,
)
from app.db.base import utc_now
from app.db.models.knowledge_item import KnowledgeItemTable


@pytest.mark.asyncio
async def test_ingest_pack_and_retrieve_approved(
    database_url: str,
) -> None:
    from app.db.session import get_session_factory, init_db, reset_db_state
    from sqlmodel import SQLModel
    from app.db.session import get_engine

    reset_db_state()
    await init_db()
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    factory = get_session_factory()
    async with factory() as session:
        rows = await ingest_approved_content_pack(session)
        assert len(rows) >= 7
        assert all(r.status == KnowledgeItemStatus.APPROVED for r in rows)

        owner = uuid4()
        result = await KnowledgeRetrievalAdapter(session).retrieve(
            KnowledgeRetrievalRequest(
                skill_code=SpecialistSkillCode.CONTENT_TELEGRAM_POST.value,
                owner_id=owner,
                locale="ru",
            )
        )
        codes = {i.code for i in result.items}
        assert "ms.const.invariants.ru" in codes or "ms.const.invariants.en" in codes
        assert "ms.content.telegram_methodology" in codes
        assert "ms.content.telegram_output_template" in codes
        assert result.retrieval_policy_version == RETRIEVAL_POLICY_VERSION
        assert result.items[0].knowledge_type == KnowledgeType.CONSTITUTIONAL_POLICY


@pytest.mark.asyncio
async def test_exclusions_and_tenancy(database_url: str) -> None:
    from app.db.session import get_session_factory, init_db, reset_db_state, get_engine
    from sqlmodel import SQLModel

    reset_db_state()
    await init_db()
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    factory = get_session_factory()
    owner_a = uuid4()
    owner_b = uuid4()
    project_a = uuid4()
    project_b = uuid4()

    async with factory() as session:
        await ingest_approved_content_pack(session)
        now = utc_now()
        session.add(
            KnowledgeItemTable(
                code="ms.test.candidate",
                title="Candidate",
                knowledge_type=KnowledgeType.DOMAIN_METHODOLOGY,
                domain=KnowledgeDomain.CONTENT,
                content="cand",
                content_format=KnowledgeContentFormat.MARKDOWN,
                content_hash=content_hash("cand"),
                source_uri="canonical://test/candidate",
                source_hash="x",
                version="1.0",
                status=KnowledgeItemStatus.CANDIDATE,
                authority=KnowledgeAuthority.PRODUCT,
                tenant_scope=KnowledgeTenantScope.GLOBAL,
                locale="en",
                valid_from=now,
                citation_required=False,
                tags=["telegram", "content"],
                specialist_roles=["content_specialist"],
                metadata_json={},
            )
        )
        session.add(
            KnowledgeItemTable(
                code="ms.test.rejected",
                title="Rejected",
                knowledge_type=KnowledgeType.DOMAIN_METHODOLOGY,
                domain=KnowledgeDomain.CONTENT,
                content="rej",
                content_format=KnowledgeContentFormat.MARKDOWN,
                content_hash=content_hash("rej"),
                source_uri="canonical://test/rejected",
                version="1.0",
                status=KnowledgeItemStatus.REJECTED,
                authority=KnowledgeAuthority.PRODUCT,
                tenant_scope=KnowledgeTenantScope.GLOBAL,
                locale="en",
                valid_from=now,
                citation_required=False,
                tags=["telegram"],
                specialist_roles=["content_specialist"],
                metadata_json={},
            )
        )
        session.add(
            KnowledgeItemTable(
                code="ms.test.owner_a",
                title="Owner A brand",
                knowledge_type=KnowledgeType.EXAMPLE,
                domain=KnowledgeDomain.CONTENT,
                content="brand a",
                content_format=KnowledgeContentFormat.MARKDOWN,
                content_hash=content_hash("brand a"),
                source_uri="canonical://test/owner_a",
                version="1.0",
                status=KnowledgeItemStatus.APPROVED,
                authority=KnowledgeAuthority.OWNER,
                tenant_scope=KnowledgeTenantScope.OWNER,
                owner_id=owner_a,
                locale="ru",
                valid_from=now,
                citation_required=False,
                tags=["brand", "content"],
                specialist_roles=["content_specialist"],
                metadata_json={},
                reviewed_at=now,
                reviewed_by="test",
            )
        )
        session.add(
            KnowledgeItemTable(
                code="ms.test.project_a",
                title="Project A",
                knowledge_type=KnowledgeType.PROJECT_KNOWLEDGE,
                domain=KnowledgeDomain.CONTENT,
                content="proj",
                content_format=KnowledgeContentFormat.MARKDOWN,
                content_hash=content_hash("proj"),
                source_uri="project://a",
                version="1.0",
                status=KnowledgeItemStatus.APPROVED,
                authority=KnowledgeAuthority.PROJECT,
                tenant_scope=KnowledgeTenantScope.PROJECT,
                owner_id=owner_a,
                project_id=project_a,
                locale="ru",
                valid_from=now,
                citation_required=True,
                tags=["content"],
                specialist_roles=["content_specialist"],
                metadata_json={},
                reviewed_at=now,
                reviewed_by="test",
            )
        )
        await session.commit()

        adapter = KnowledgeRetrievalAdapter(session)
        for_a = await adapter.retrieve(
            KnowledgeRetrievalRequest(
                skill_code="content.telegram_post",
                owner_id=owner_a,
                project_id=project_a,
                locale="ru",
            )
        )
        codes_a = {i.code for i in for_a.items}
        assert "ms.test.candidate" not in codes_a
        assert "ms.test.rejected" not in codes_a
        assert "ms.test.owner_a" in codes_a
        assert "ms.test.project_a" in codes_a

        for_b = await adapter.retrieve(
            KnowledgeRetrievalRequest(
                skill_code="content.telegram_post",
                owner_id=owner_b,
                project_id=project_b,
                locale="ru",
            )
        )
        codes_b = {i.code for i in for_b.items}
        assert "ms.test.owner_a" not in codes_b
        assert "ms.test.project_a" not in codes_b


@pytest.mark.asyncio
async def test_snapshot_immutable_after_supersede(database_url: str) -> None:
    from app.db.session import get_session_factory, init_db, reset_db_state, get_engine
    from sqlmodel import SQLModel

    reset_db_state()
    await init_db()
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    factory = get_session_factory()
    owner = uuid4()
    async with factory() as session:
        await ingest_approved_content_pack(session)
        retrieval = await KnowledgeRetrievalAdapter(session).retrieve(
            KnowledgeRetrievalRequest(
                skill_code="content.telegram_post",
                owner_id=owner,
                locale="ru",
            )
        )
        snap = await KnowledgeSnapshotService(session).create_from_retrieval(
            owner_id=owner,
            project_id=None,
            skill_code="content.telegram_post",
            skill_version="1.0",
            capability_pack_version="1.0",
            locale="ru",
            retrieval=retrieval,
        )
        old_hash = snap.snapshot_hash
        old_refs = list(snap.item_refs)

        # supersede methodology
        store = KnowledgeStoreService(session)
        method = await store.get_by_code_version("ms.content.telegram_methodology", "1.0")
        assert method is not None
        await store.supersede(
            method.id,
            content=method.content + "\n\n## v1.1 note\n",
            version="1.1",
            reviewed_by="tester",
            rationale="methodology bump",
        )

        # old snapshot unchanged
        await session.refresh(snap)
        assert snap.snapshot_hash == old_hash
        assert snap.item_refs == old_refs

        # new retrieval sees new version
        retrieval2 = await KnowledgeRetrievalAdapter(session).retrieve(
            KnowledgeRetrievalRequest(
                skill_code="content.telegram_post",
                owner_id=owner,
                locale="ru",
            )
        )
        versions = {
            i.code: i.version
            for i in retrieval2.items
            if i.code == "ms.content.telegram_methodology"
        }
        assert versions.get("ms.content.telegram_methodology") == "1.1"


def test_telegram_post_flow_api(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    # Ensure pack present
    pack = client.post(
        "/knowledge-foundation/items/ingest-content-pack",
        headers=auth_headers,
    )
    assert pack.status_code == 200
    assert len(pack.json()) >= 7

    first = client.post(
        "/user-requests",
        headers=auth_headers,
        json={"text": "Напиши пост для Telegram."},
    )
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["skill_code"] == "content.telegram_post"
    assert body["execution_readiness"] == "needs_clarification"
    assert body["status"] == "needs_clarification"
    assert body["missing_inputs"]
    assert body["knowledge_snapshot_id"] is None

    clarified = client.post(
        f"/user-requests/{body['id']}/clarify",
        headers=auth_headers,
        json={
            "answer": "Уточнения по полям",
            "skill_inputs": {
                "topic": "бурение скважин",
                "audience": "B2B закупщики",
                "objective": "заявки в Direct",
                "tone": "деловой",
                "length": "короткий",
                "CTA": "написать в Telegram",
                "factuality_mode": "strict",
                "platform": "Telegram",
            },
        },
    )
    assert clarified.status_code == 200, clarified.text
    ready = clarified.json()
    assert ready["skill_code"] == "content.telegram_post"
    assert ready["skill_version"] == "1.0"
    assert ready["capability_pack_code"] == "content_specialist"
    assert ready["execution_readiness"] == "ready_for_draft"
    assert ready["status"] == "ready_for_draft"
    assert ready["knowledge_snapshot_id"]
    assert ready["knowledge_snapshot_hash"]
    assert ready["approved_knowledge_count"] >= 1
    assert "не генерирую" in ready["assistant_message"].lower() or "draft" in ready[
        "assistant_message"
    ].lower() or "черновик" in ready["assistant_message"].lower()

    listed = client.get("/user-requests", headers=auth_headers)
    assert listed.status_code == 200
    match = next(r for r in listed.json() if r["id"] == ready["id"])
    assert match["knowledge_snapshot_hash"] == ready["knowledge_snapshot_hash"]
    assert match["skill_code"] == "content.telegram_post"

    policy = client.get("/knowledge-foundation/policy", headers=auth_headers)
    assert policy.json()["embeddings_enabled"] is False
    assert policy.json()["llm_enabled"] is False
    assert policy.json()["execution_enabled"] is False


def test_snapshot_hash_stable() -> None:
    refs = [
        {
            "knowledge_item_id": "11111111-1111-4111-8111-111111111111",
            "code": "a",
            "version": "1.0",
            "content_hash": "sha256:abc",
        },
        {
            "knowledge_item_id": "22222222-2222-4222-8222-222222222222",
            "code": "b",
            "version": "1.0",
            "content_hash": "sha256:def",
        },
    ]
    h1 = compute_snapshot_hash(
        skill_code="content.telegram_post",
        skill_version="1.0",
        capability_pack_version="1.0",
        retrieval_policy_version="1.0",
        locale="ru",
        item_refs=refs,
    )
    h2 = compute_snapshot_hash(
        skill_code="content.telegram_post",
        skill_version="1.0",
        capability_pack_version="1.0",
        retrieval_policy_version="1.0",
        locale="ru",
        item_refs=list(reversed(refs)),
    )
    assert h1 == h2
    assert h1.startswith("sha256:")
