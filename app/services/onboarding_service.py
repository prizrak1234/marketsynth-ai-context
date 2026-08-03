"""First-run onboarding status (Phase AI.86)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_chat import AgentChatMessageTable, AgentChatSessionTable
from app.db.models.marketing import ContentAssetTable
from app.db.models.project import ProjectTable
from app.db.models.publication_package_job import PublicationPackageJobTable
from app.db.models.user import UserTable
from app.schemas.contracts import ONBOARDING_MANUAL_STEPS, AgentType, OnboardingStep
from app.schemas.onboarding import OnboardingStatusResponse, OnboardingStepStatus
from app.services.agents import AgentService
from app.services.e2e_demo_seed_service import E2E_DEMO_PROJECT_NAME
from app.services.projects_service import ProjectService
from app.services.users_service import UserService
from app.core.exceptions import InvalidStateError

_ALL_STEPS: tuple[OnboardingStep, ...] = (
    OnboardingStep.PROJECT_CREATED,
    OnboardingStep.AGENTS_SEEDED,
    OnboardingStep.DEMO_SEEDED,
    OnboardingStep.FIRST_CHAT_DONE,
    OnboardingStep.FIRST_ASSET_CREATED,
    OnboardingStep.FIRST_PUBLICATION_JOB_CREATED,
)


class OnboardingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserService(session)
        self._projects = ProjectService(session)
        self._agents = AgentService(session)

    async def _resolve_project(
        self,
        owner_id: UUID,
        project_id: UUID | None,
    ) -> ProjectTable | None:
        if project_id is not None:
            project = await self._projects.get_by_id(project_id)
            if project is None or project.owner_id != owner_id:
                return None
            return project
        projects = await self._projects.list(user_id=owner_id, limit=1)
        return projects[0] if projects else None

    async def _manual_completed(self, user: UserTable, step: OnboardingStep) -> bool:
        raw = user.onboarding_manual_completed or []
        return step.value in raw

    async def get_status(
        self,
        owner_id: UUID,
        *,
        project_id: UUID | None = None,
    ) -> OnboardingStatusResponse | None:
        user = await self._users.get_by_id(owner_id)
        if user is None:
            return None

        project_count = int(
            (
                await self._session.execute(
                    select(func.count()).select_from(ProjectTable).where(
                        ProjectTable.owner_id == owner_id,
                    ),
                )
            ).scalar_one()
            or 0,
        )
        project = await self._resolve_project(owner_id, project_id)

        flags: dict[OnboardingStep, bool] = {
            OnboardingStep.PROJECT_CREATED: project_count > 0,
            OnboardingStep.AGENTS_SEEDED: False,
            OnboardingStep.DEMO_SEEDED: await self._manual_completed(
                user,
                OnboardingStep.DEMO_SEEDED,
            ),
            OnboardingStep.FIRST_CHAT_DONE: False,
            OnboardingStep.FIRST_ASSET_CREATED: False,
            OnboardingStep.FIRST_PUBLICATION_JOB_CREATED: False,
        }

        if project is not None:
            agents = await self._agents.list_agents(owner_id, project_id=project.id)
            types = {a.type for a in agents}
            flags[OnboardingStep.AGENTS_SEEDED] = (
                AgentType.ORCHESTRATOR in types and AgentType.COPYWRITER in types
            )
            if project.name == E2E_DEMO_PROJECT_NAME:
                flags[OnboardingStep.DEMO_SEEDED] = True

            chat_count = int(
                (
                    await self._session.execute(
                        select(func.count()).select_from(AgentChatMessageTable).join(
                            AgentChatSessionTable,
                            AgentChatMessageTable.session_id == AgentChatSessionTable.id,
                        ).where(
                            AgentChatSessionTable.owner_id == owner_id,
                            AgentChatSessionTable.project_id == project.id,
                        ),
                    )
                ).scalar_one()
                or 0,
            )
            flags[OnboardingStep.FIRST_CHAT_DONE] = chat_count > 0

            asset_count = int(
                (
                    await self._session.execute(
                        select(func.count()).select_from(ContentAssetTable).where(
                            ContentAssetTable.owner_id == owner_id,
                            ContentAssetTable.project_id == project.id,
                        ),
                    )
                ).scalar_one()
                or 0,
            )
            flags[OnboardingStep.FIRST_ASSET_CREATED] = asset_count > 0

            job_count = int(
                (
                    await self._session.execute(
                        select(func.count()).select_from(PublicationPackageJobTable).where(
                            PublicationPackageJobTable.owner_id == owner_id,
                            PublicationPackageJobTable.project_id == project.id,
                        ),
                    )
                ).scalar_one()
                or 0,
            )
            flags[OnboardingStep.FIRST_PUBLICATION_JOB_CREATED] = job_count > 0

        steps: list[OnboardingStepStatus] = []
        for step in _ALL_STEPS:
            manual = step in ONBOARDING_MANUAL_STEPS
            completed = flags[step]
            if step == OnboardingStep.DEMO_SEEDED:
                auto_demo = project is not None and project.name == E2E_DEMO_PROJECT_NAME
                derived = auto_demo or not completed
                if auto_demo:
                    completed = True
            else:
                derived = True
            steps.append(
                OnboardingStepStatus(
                    step=step,
                    completed=completed,
                    derived=derived,
                    manual_allowed=manual,
                ),
            )

        completed_count = sum(1 for item in steps if item.completed)
        return OnboardingStatusResponse(
            project_id=str(project.id) if project else None,
            steps=steps,
            completed_count=completed_count,
            total_count=len(steps),
        )

    async def complete_manual_step(
        self,
        owner_id: UUID,
        step: OnboardingStep,
    ) -> OnboardingStatusResponse | None:
        if step not in ONBOARDING_MANUAL_STEPS:
            raise InvalidStateError(
                f"Step {step.value} cannot be completed manually; it is derived from product data",
            )
        user = await self._users.get_by_id(owner_id)
        if user is None:
            return None
        manual = list(user.onboarding_manual_completed or [])
        if step.value not in manual:
            manual.append(step.value)
        from app.db.repositories.user_repo import UserRepository

        user.onboarding_manual_completed = manual
        await UserRepository(self._session).update(user)
        return await self.get_status(owner_id)
