"""KG.2 — Operational Knowledge Governance tests (no VectorDB / no external LLM)."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app.db.base import utc_now
from app.knowledge_governance.benchmark_runner import load_pack_cases, run_benchmark
from app.knowledge_governance.citation_gate import CitationGateError, enforce_and_persist_citations
from app.knowledge_governance.governed_snapshot import (
    InsufficientGovernedKnowledgeError,
    create_governed_snapshot,
)
from app.knowledge_governance.lifecycle import LifecycleError, assert_transition, can_transition
from app.knowledge_governance.operator import KnowledgeGovernanceOperator
from app.schemas.contracts import KnowledgeDomain, KnowledgeGovernanceStatus


async def _schema() -> None:
    from app.db.session import get_engine, init_db, reset_db_state

    reset_db_state()
    await init_db()
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


@pytest.mark.asyncio
async def test_lifecycle_forbidden_draft_to_published(database_url: str) -> None:
    assert not can_transition(
        KnowledgeGovernanceStatus.DRAFT, KnowledgeGovernanceStatus.PUBLISHED
    )
    with pytest.raises(LifecycleError) as exc:
        assert_transition(
            KnowledgeGovernanceStatus.DRAFT, KnowledgeGovernanceStatus.PUBLISHED
        )
    assert exc.value.code == "draft_to_published_forbidden"


@pytest.mark.asyncio
async def test_admission_publish_and_immutable_version(database_url: str) -> None:
    await _schema()
    from app.db.session import get_session_factory

    factory = get_session_factory()
    tenant = uuid4()
    async with factory() as session:
        # Need a real user FK — create via SQLModel UserTable
        from app.db.models.user import UserTable

        user = UserTable(
            id=tenant,
            telegram_id=9_100_001,
            display_name="KG Owner",
            is_active=True,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(user)
        await session.commit()

        op = KnowledgeGovernanceOperator(session)
        created = await op.create_candidate(
            tenant_owner_id=tenant,
            actor_user_id=tenant,
            code="drill.safety.v1",
            title="Буровая безопасность",
            content=(
                "# Flow check\nПеред подъёмом обязателен flow check.\n"
                "# Near miss\nВсе near miss фиксируются.\n"
            ),
            source_uri="canonical://drilling/safety",
            domain=KnowledgeDomain.OPERATIONS,
        )
        object_id = created["object_id"]
        version_id = created["version_id"]

        with pytest.raises(LifecycleError):
            await op.publish_version(
                tenant_owner_id=tenant, actor_user_id=tenant, version_id=__import__("uuid").UUID(version_id)
            )

        await op.assign_owner(
            tenant_owner_id=tenant,
            actor_user_id=tenant,
            object_id=__import__("uuid").UUID(object_id),
            owner_user_id=tenant,
            reviewer_user_id=tenant,
        )
        await op.review_version(
            tenant_owner_id=tenant,
            actor_user_id=tenant,
            version_id=__import__("uuid").UUID(version_id),
            decision="approve",
            next_review_days=90,
        )
        pub = await op.publish_version(
            tenant_owner_id=tenant,
            actor_user_id=tenant,
            version_id=__import__("uuid").UUID(version_id),
        )
        assert pub["status"] == "published"

        detail = await op.get_object_detail(
            tenant_owner_id=tenant, object_id=__import__("uuid").UUID(object_id)
        )
        assert len(detail["semantic_chunks"]) >= 1
        assert detail["versions"][0]["status"] == "published"
        content_before = detail["versions"][0]["source_uri"]

        # Immutable: supersede creates new draft, old stays superseded with same source
        sup = await op.supersede_version(
            tenant_owner_id=tenant,
            actor_user_id=tenant,
            version_id=__import__("uuid").UUID(version_id),
            new_content="# Flow check\nОбновлённое правило.\n",
            new_version="2.0",
        )
        assert sup["replacement_status"] == "draft"
        detail2 = await op.get_object_detail(
            tenant_owner_id=tenant, object_id=__import__("uuid").UUID(object_id)
        )
        old = next(v for v in detail2["versions"] if v["id"] == version_id)
        assert old["status"] == "superseded"
        assert old["source_uri"] == content_before


@pytest.mark.asyncio
async def test_freshness_excludes_expired_from_snapshot(database_url: str) -> None:
    await _schema()
    from app.db.models.user import UserTable
    from app.db.session import get_session_factory
    from uuid import UUID

    factory = get_session_factory()
    tenant = uuid4()
    async with factory() as session:
        session.add(
            UserTable(
                id=tenant,
                telegram_id=9_100_002,
                display_name="KG Fresh",
                is_active=True,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
        )
        await session.commit()
        op = KnowledgeGovernanceOperator(session)
        created = await op.create_candidate(
            tenant_owner_id=tenant,
            actor_user_id=tenant,
            code="drill.expired",
            title="Expired pack",
            content="# Rule\nMust expire.\n",
            source_uri="canonical://drilling/expired",
        )
        vid = UUID(created["version_id"])
        oid = UUID(created["object_id"])
        await op.assign_owner(
            tenant_owner_id=tenant,
            actor_user_id=tenant,
            object_id=oid,
            owner_user_id=tenant,
            reviewer_user_id=tenant,
        )
        await op.review_version(
            tenant_owner_id=tenant,
            actor_user_id=tenant,
            version_id=vid,
            decision="approve",
            next_review_days=90,
        )
        await op.publish_version(
            tenant_owner_id=tenant, actor_user_id=tenant, version_id=vid
        )
        from app.db.models.knowledge_governance import KnowledgeVersionTable

        ver = await session.get(KnowledgeVersionTable, vid)
        assert ver is not None
        ver.next_review_at = utc_now() - timedelta(days=1)
        session.add(ver)
        await session.commit()

        with pytest.raises(InsufficientGovernedKnowledgeError):
            await create_governed_snapshot(
                session,
                tenant_owner_id=tenant,
                skill_code="content.telegram_post",
                require_knowledge=True,
            )


@pytest.mark.asyncio
async def test_tenant_isolation_snapshot(database_url: str) -> None:
    await _schema()
    from app.db.models.user import UserTable
    from app.db.session import get_session_factory
    from uuid import UUID

    factory = get_session_factory()
    a, b = uuid4(), uuid4()
    async with factory() as session:
        for uid, tid in ((a, 9_100_003), (b, 9_100_004)):
            session.add(
                UserTable(
                    id=uid,
                    telegram_id=tid,
                    display_name=str(uid),
                    is_active=True,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
        await session.commit()
        op = KnowledgeGovernanceOperator(session)
        created = await op.create_candidate(
            tenant_owner_id=a,
            actor_user_id=a,
            code="tenant.a.only",
            title="Tenant A",
            content="# A\nSecret for A\n",
            source_uri="canonical://a/secret",
        )
        vid = UUID(created["version_id"])
        oid = UUID(created["object_id"])
        await op.assign_owner(
            tenant_owner_id=a,
            actor_user_id=a,
            object_id=oid,
            owner_user_id=a,
            reviewer_user_id=a,
        )
        await op.review_version(
            tenant_owner_id=a,
            actor_user_id=a,
            version_id=vid,
            decision="approve",
        )
        await op.publish_version(tenant_owner_id=a, actor_user_id=a, version_id=vid)

        with pytest.raises(InsufficientGovernedKnowledgeError):
            await create_governed_snapshot(
                session,
                tenant_owner_id=b,
                skill_code="content.telegram_post",
                require_knowledge=True,
            )
        snap = await create_governed_snapshot(
            session,
            tenant_owner_id=a,
            skill_code="content.telegram_post",
            require_knowledge=True,
        )
        assert snap.governance_meta is not None
        assert len(snap.governance_meta["knowledge_version_ids"]) == 1


@pytest.mark.asyncio
async def test_citation_gate_blocks_missing_source(database_url: str) -> None:
    await _schema()
    from app.db.models.user import UserTable
    from app.db.session import get_session_factory

    factory = get_session_factory()
    tenant = uuid4()
    async with factory() as session:
        session.add(
            UserTable(
                id=tenant,
                telegram_id=9_100_005,
                display_name="Cite",
                is_active=True,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
        )
        await session.commit()
        with pytest.raises(CitationGateError):
            await enforce_and_persist_citations(
                session,
                tenant_owner_id=tenant,
                user_request_id=None,
                snapshot_id=None,
                skill_code="content.telegram_post",
                claims=[{"claim_id": "1", "claim_text": "факт без источника"}],
                citation_required=True,
            )


@pytest.mark.asyncio
async def test_benchmark_pack_and_runner_no_llm(database_url: str) -> None:
    await _schema()
    from app.db.models.user import UserTable
    from app.db.session import get_session_factory

    cases = load_pack_cases()
    assert len(cases) >= 30
    factory = get_session_factory()
    tenant = uuid4()
    async with factory() as session:
        session.add(
            UserTable(
                id=tenant,
                telegram_id=9_100_006,
                display_name="Bench",
                is_active=True,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
        )
        await session.commit()
        result = await run_benchmark(session, tenant_owner_id=tenant)
        assert result["llm_called"] is False
        assert result["case_count"] >= 30


def test_operator_api_endpoints(
    client: TestClient, auth_headers: dict[str, str], other_auth_headers: dict[str, str]
) -> None:
    create = client.post(
        "/knowledge-governance/candidates",
        headers=auth_headers,
        json={
            "code": "api.drill.1",
            "title": "API Drill",
            "content": "# PPE\nСИЗ обязательны.\n",
            "source_uri": "canonical://api/drill",
            "domain": "operations",
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    object_id = body["object_id"]
    version_id = body["version_id"]

    # other tenant cannot see
    foreign = client.get(
        f"/knowledge-governance/objects/{object_id}", headers=other_auth_headers
    )
    assert foreign.status_code == 404

    # Resolve current user id via users list or object detail after assign with self
    # Auth key user owns candidates; assign-owner uses owner_user_id from detail list
    objs = client.get("/knowledge-governance/objects", headers=auth_headers)
    assert objs.status_code == 200
    assert any(o["id"] == object_id for o in objs.json()["objects"])

    # Use users endpoint if available; fallback: create second key not needed —
    # assign to self by reading user from API key introspection isn't exposed,
    # so assign using a project create which returns owner.
    project = client.post(
        "/projects",
        headers=auth_headers,
        json={"name": "KG Test Project", "description": "kg2"},
    )
    assert project.status_code in {200, 201}, project.text
    # Get owner from project
    proj_id = project.json()["id"]
    proj_get = client.get(f"/projects/{proj_id}", headers=auth_headers)
    assert proj_get.status_code == 200
    user_id = proj_get.json().get("owner_id") or proj_get.json().get("ownerId")
    assert user_id

    assign = client.post(
        f"/knowledge-governance/objects/{object_id}/assign-owner",
        headers=auth_headers,
        json={"owner_user_id": user_id, "reviewer_user_id": user_id},
    )
    assert assign.status_code == 200, assign.text

    validate = client.post(
        f"/knowledge-governance/versions/{version_id}/validate",
        headers=auth_headers,
        json={"decision": "approve", "next_review_days": 60},
    )
    assert validate.status_code == 200, validate.text
    assert validate.json()["status"] == "validated"

    publish = client.post(
        f"/knowledge-governance/versions/{version_id}/publish",
        headers=auth_headers,
        json={},
    )
    assert publish.status_code == 200, publish.text
    assert publish.json()["status"] == "published"

    cand = client.get("/knowledge-governance/candidates", headers=auth_headers)
    assert cand.status_code == 200
    fresh = client.get("/knowledge-governance/freshness", headers=auth_headers)
    assert fresh.status_code == 200
    benches = client.get("/knowledge-governance/benchmarks", headers=auth_headers)
    assert benches.status_code == 200
    assert benches.json()["count"] >= 1
