"""Idempotent demo seed for internal ops UI (Phase UI.10).

Creates project, campaign, Telegram channel, plan draft, generated draft assets,
one approved asset, one scheduled publication job, and one pending review asset.

Usage:
    uv run python scripts/seed_demo_marketing_flow.py
    uv run python scripts/seed_demo_marketing_flow.py --refresh-api-key
    uv run python scripts/seed_demo_marketing_flow.py --reset-db
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime, timedelta
from typing import Any
from pathlib import Path
from uuid import UUID

from sqlmodel import SQLModel

import app.db.models  # noqa: F401 — register tables for create_all
from app.core.config import get_settings
from app.db.repositories.user_repo import UserRepository
from app.db.session import close_db, get_engine, get_session_factory, init_db, reset_db_state
from app.marketing.contracts import ContentAssetStatus, MarketingCampaignStatus
from app.publishing.contracts import PublicationJobStatus, PublishingChannelType
from app.schemas.contracts import AgentType, UserRole
from app.schemas.crud import AgentCreateRequest, ProjectCreate, UserCreate
from app.schemas.publishing import PublicationJobCreateRequest, PublishingChannelCreateRequest
from app.services.auth import AuthService
from app.services.campaign_plan_draft_service import CampaignPlanDraftService
from app.services.content_asset_service import ContentAssetService
from app.services.marketing_campaign_service import MarketingCampaignService
from app.services.agents import AgentService
from app.services.projects_service import ProjectService
from app.services.publication_job_service import PublicationJobService
from app.services.publishing_channel_service import PublishingChannelService
from app.services.users_service import UserService

DEMO_TELEGRAM_ID = 9_000_100
DEMO_USER_EMAIL = "demo@botfazer.local"
DEMO_USER_NAME = "Demo Marketing User"
DEMO_PROJECT_NAME = "Demo Marketing Project"
DEMO_CAMPAIGN_TITLE = "Q2 Launch Demo"
DEMO_CHANNEL_NAME = "Demo Telegram"
DEMO_PLAN_TITLE = "Demo launch plan"
DEMO_API_KEY_NAME = "Demo marketing flow key"
DEMO_MARKETER_AGENT_TYPES: tuple[AgentType, ...] = (
    AgentType.GENERAL,
    AgentType.PROGRAMMER,
    AgentType.MEDIA,
    AgentType.ORCHESTRATOR,
    AgentType.RESEARCHER,
    AgentType.STRATEGIST,
    AgentType.COPYWRITER,
)


def _demo_plan_payload() -> dict[str, Any]:
    return {
        "goal": "Launch product update in Telegram",
        "target_audience": "SMB operators",
        "key_message": "Ship faster with BotFazer",
        "content_items": [
            {
                "title": "Launch announcement",
                "channel": "telegram",
                "format": "text",
                "notes": "Hero post for demo",
            },
            {
                "title": "Feature highlight",
                "channel": "telegram",
                "format": "text",
                "notes": "Pending human review",
            },
            {
                "title": "Social proof",
                "channel": "telegram",
                "format": "text",
                "notes": "Optional extra draft",
            },
        ],
    }


def _sqlite_path_from_url(database_url: str) -> Path | None:
    prefix = "sqlite+aiosqlite:///"
    if database_url.startswith(prefix):
        raw = database_url.removeprefix(prefix)
        return Path(raw) if raw != ":memory:" else None
    return None


def _reset_sqlite_database() -> None:
    settings = get_settings()
    db_path = _sqlite_path_from_url(settings.database_url)
    if db_path is None:
        raise RuntimeError("--reset-db only supports local sqlite+aiosqlite file databases")
    reset_db_state()
    if db_path.exists():
        db_path.unlink()
        print(f"Removed database file {db_path}")


async def _ensure_schema(*, reset_db: bool) -> None:
    if reset_db:
        await asyncio.to_thread(_reset_sqlite_database)
    await init_db()
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def _mint_demo_api_key(
    auth: AuthService,
    user_id: UUID,
    *,
    refresh: bool,
) -> str:
    existing = await auth.list_api_keys(user_id)
    for row in existing:
        if row.name == DEMO_API_KEY_NAME and row.revoked_at is None:
            if refresh:
                await auth.revoke_api_key(row.id, user_id)
            else:
                raise RuntimeError(
                    "Demo API key already exists. Re-run with --refresh-api-key "
                    "to mint a new key, or use your saved plain key.",
                )

    created = await auth.create_api_key(user_id, DEMO_API_KEY_NAME)
    return created.plain_key


async def run_demo_seed(*, refresh_api_key: bool, reset_db: bool) -> None:
    await _ensure_schema(reset_db=reset_db)
    factory = get_session_factory()

    async with factory() as session:
        user_repo = UserRepository(session)
        user_service = UserService(session)
        project_service = ProjectService(session)
        auth_service = AuthService(session)
        campaign_service = MarketingCampaignService(session)
        channel_service = PublishingChannelService(session)
        plan_service = CampaignPlanDraftService(session)
        asset_service = ContentAssetService(session)
        job_service = PublicationJobService(session)
        agent_service = AgentService(session)

        user = await user_repo.get_by_telegram_id(DEMO_TELEGRAM_ID)
        if user is None:
            user = await user_service.create(
                UserCreate(
                    telegram_id=DEMO_TELEGRAM_ID,
                    email=DEMO_USER_EMAIL,
                    display_name=DEMO_USER_NAME,
                    role=UserRole.OWNER,
                    is_active=True,
                ),
            )
            print(f"Created user {user.id}")
        else:
            print(f"User already exists {user.id}")

        owner_id = user.id

        plain_key = await _mint_demo_api_key(
            auth_service,
            owner_id,
            refresh=refresh_api_key,
        )

        projects = await project_service.list(user_id=owner_id)
        project = next((p for p in projects if p.name == DEMO_PROJECT_NAME), None)
        if project is None:
            project = await project_service.create(
                ProjectCreate(
                    owner_id=owner_id,
                    name=DEMO_PROJECT_NAME,
                    description="Demo data for internal ops UI",
                ),
            )
            print(f"Created project {project.id}")
        else:
            print(f"Project already exists {project.id}")

        project_id = project.id

        marketer_agent_ids: dict[str, str] = {}
        project_agents = await agent_service.list_agents(owner_id, project_id=project_id)
        for agent_type in DEMO_MARKETER_AGENT_TYPES:
            existing = next((a for a in project_agents if a.type == agent_type), None)
            if existing is None:
                created_agent = await agent_service.create_agent(
                    owner_id,
                    AgentCreateRequest(project_id=project_id, type=agent_type),
                )
                if created_agent is None:
                    raise RuntimeError(f"failed to create demo {agent_type.value} agent")
                existing = created_agent
                print(f"Created {agent_type.value} agent {existing.id}")
            activated = await agent_service.activate_agent(existing.id, owner_id)
            if activated is None:
                raise RuntimeError(f"failed to activate {agent_type.value} agent")
            marketer_agent_ids[agent_type.value] = str(activated.id)
            project_agents.append(activated)
            print(f"{agent_type.value} agent active {activated.id}")

        campaigns = await campaign_service.list_by_project(owner_id, project_id)
        campaign = next((c for c in (campaigns or []) if c.title == DEMO_CAMPAIGN_TITLE), None)
        if campaign is None:
            campaign = await campaign_service.create(
                owner_id,
                project_id,
                brief_id=None,
                title=DEMO_CAMPAIGN_TITLE,
                description="End-to-end demo campaign for UI walkthrough",
                status=MarketingCampaignStatus.ACTIVE,
                start_at=None,
                end_at=None,
                campaign_metadata={"demo_seed": True},
            )
            if campaign is None:
                raise RuntimeError("failed to create demo campaign")
            print(f"Created campaign {campaign.id}")
        else:
            print(f"Campaign already exists {campaign.id}")

        campaign_id = campaign.id

        channels = await channel_service.list(owner_id, project_id, include_archived=True)
        channel = next((c for c in (channels or []) if c.name == DEMO_CHANNEL_NAME), None)
        if channel is None:
            channel = await channel_service.create(
                owner_id,
                project_id,
                PublishingChannelCreateRequest(
                    name=DEMO_CHANNEL_NAME,
                    type=PublishingChannelType.TELEGRAM,
                    config={"chat_id": "-1001234567890", "parse_mode": "HTML"},
                ),
            )
            if channel is None:
                raise RuntimeError("failed to create demo Telegram channel")
            print(f"Created channel {channel.id}")
        else:
            print(f"Channel already exists {channel.id}")

        channel_id = channel.id

        plan_drafts = await plan_service.list_by_campaign(
            owner_id,
            project_id,
            campaign_id,
            include_archived=True,
        )
        plan_draft = next(
            (d for d in (plan_drafts or []) if d.title == DEMO_PLAN_TITLE),
            None,
        )
        if plan_draft is None:
            plan_draft = await plan_service.create(
                owner_id,
                project_id,
                campaign_id,
                title=DEMO_PLAN_TITLE,
                plan_payload=_demo_plan_payload(),
            )
            if plan_draft is None:
                raise RuntimeError("failed to create demo plan draft")
            print(f"Created plan draft {plan_draft.id}")
        else:
            print(f"Plan draft already exists {plan_draft.id}")

        draft_id = plan_draft.id

        gen_result = await plan_service.generate_assets(
            owner_id,
            project_id,
            campaign_id,
            draft_id,
        )
        if gen_result is None:
            raise RuntimeError("failed to generate assets from plan draft")
        print(
            f"Plan assets: created={gen_result.created_count} "
            f"already_generated={gen_result.already_generated} "
            f"count={len(gen_result.asset_ids)}",
        )

        draft_assets = await asset_service.list_drafts_for_plan_draft(
            owner_id,
            project_id,
            campaign_id,
            draft_id,
        )
        if len(draft_assets) < 2:
            raise RuntimeError("expected at least two draft assets from plan draft")

        approved_asset = next(
            (row for row in draft_assets if row.status == ContentAssetStatus.APPROVED),
            None,
        )
        if approved_asset is None:
            approved_asset = await asset_service.approve_asset(
                owner_id,
                project_id,
                draft_assets[0].id,
            )
            if approved_asset is None:
                raise RuntimeError("failed to approve demo asset")
            print(f"Approved asset {approved_asset.id}")
        else:
            print(f"Approved asset already set {approved_asset.id}")

        draft_assets = await asset_service.list_drafts_for_plan_draft(
            owner_id,
            project_id,
            campaign_id,
            draft_id,
        )

        review_asset = next(
            (row for row in draft_assets if row.status == ContentAssetStatus.DRAFT),
            None,
        )
        if review_asset is None:
            raise RuntimeError("expected at least one draft asset pending review")
        print(f"Pending review asset {review_asset.id}")

        jobs = await job_service.list(owner_id, project_id, limit=200)
        scheduled_job = next(
            (
                job
                for job in (jobs or [])
                if job.status == PublicationJobStatus.SCHEDULED
                and job.asset_id == approved_asset.id
            ),
            None,
        )
        if scheduled_job is None and approved_asset is not None:
            scheduled_at = datetime.now(UTC) + timedelta(days=2)
            job = await job_service.create(
                owner_id,
                project_id,
                PublicationJobCreateRequest(
                    asset_id=approved_asset.id,
                    channel_id=channel_id,
                    campaign_id=campaign_id,
                    scheduled_at=scheduled_at,
                ),
            )
            if job is None:
                raise RuntimeError("failed to create scheduled publication job")
            print(f"Created scheduled publication job {job.id}")
        elif scheduled_job is not None:
            print(f"Scheduled job already exists {scheduled_job.id}")

    await close_db()

    print("")
    print("--- Copy into web/.env.local ---")
    print(f"NEXT_PUBLIC_BOTFAZER_PROJECT_ID={project_id}")
    print(f"NEXT_PUBLIC_BOTFAZER_API_KEY={plain_key}")
    print("NEXT_PUBLIC_BOTFAZER_API_BASE_URL=http://127.0.0.1:8000")
    print("---")
    print("--- Backend .env (AI chain demo — enable tools) ---")
    print("AGENT_CHAT_TOOLS_ENABLED=true")
    print("TOOLS_PROVIDER_ENABLED=true")
    print("AGENT_WRITE_TOOLS_ENABLED=true")
    print("CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED=true")
    print("CONTENT_ASSET_REVISION_WRITE_TOOL_ENABLED=true")
    print("---")
    print("--- AI.14 chain demo (after API + web dev server) ---")
    print("1. Open /agents/chat")
    print("2. Select campaign: Q2 Launch Demo")
    print("3. Agent: orchestrator (default)")
    print('4. Message: "Запусти новый продукт в Telegram"')
    print("Expected UI: Handled by Researcher → Strategist → Copywriter")
    print("         (3 run rows with status + Run details links)")
    if marketer_agent_ids.get("orchestrator"):
        print(f"Orchestrator agent_id (optional): {marketer_agent_ids['orchestrator']}")
    print("---")
    print("Demo seed complete.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed demo marketing flow for ops UI")
    parser.add_argument(
        "--refresh-api-key",
        action="store_true",
        help="Revoke existing demo API key and mint a new one (prints plain key)",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Delete local sqlite DB file and migrate from scratch (dev only)",
    )
    args = parser.parse_args()
    try:
        asyncio.run(
            run_demo_seed(
                refresh_api_key=args.refresh_api_key,
                reset_db=args.reset_db,
            ),
        )
    except RuntimeError as exc:
        if "already exists" in str(exc) and not args.refresh_api_key:
            print(f"Demo seed failed: {exc}", file=sys.stderr)
            print("Hint: uv run python scripts/seed_demo_marketing_flow.py --refresh-api-key")
            return 1
        print(f"Demo seed failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Demo seed failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
