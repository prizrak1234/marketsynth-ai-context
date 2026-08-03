"""Specialist Skill Registry diagnostics API (Phase H2.2) — no execution."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies.auth import require_active_user
from app.db.models.user import UserTable
from app.schemas.contracts import (
    SpecialistSkillCode,
    UserRequestRouteCategory,
)
from app.specialist_skills.capability_packs import (
    get_capability_pack,
    list_capability_packs,
    skill_allowed_for_specialist,
)
from app.specialist_skills.clarifications import evaluate_clarification
from app.specialist_skills.registry import get_skill, list_skills
from app.specialist_skills.route_mapping import list_route_mappings, map_route_to_skill

router = APIRouter(prefix="/specialist-skills", tags=["specialist-skills"])


@router.get("")
async def list_specialist_skills(
    current_user: UserTable = Depends(require_active_user),
) -> dict:
    _ = current_user
    skills = list_skills()
    return {
        "skills": [s.model_dump(mode="json") for s in skills],
        "count": len(skills),
        "execution_enabled": False,
        "prompts_exposed": False,
        "duplicates_agent_registry": False,
    }


@router.get("/capability-packs")
async def list_packs(
    current_user: UserTable = Depends(require_active_user),
) -> dict:
    _ = current_user
    packs = list_capability_packs()
    return {
        "packs": [p.model_dump(mode="json") for p in packs],
        "count": len(packs),
    }


@router.get("/capability-packs/{specialist_role}")
async def get_pack(
    specialist_role: str,
    current_user: UserTable = Depends(require_active_user),
) -> dict:
    _ = current_user
    pack = get_capability_pack(specialist_role)
    if pack is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pack not found")
    return pack.model_dump(mode="json")


@router.get("/route-matrix")
async def route_matrix(
    current_user: UserTable = Depends(require_active_user),
) -> dict:
    _ = current_user
    return {
        "mappings": [m.model_dump(mode="json") for m in list_route_mappings()],
    }


@router.get("/resolve")
async def resolve_route(
    route_category: UserRequestRouteCategory = Query(...),
    current_user: UserTable = Depends(require_active_user),
) -> dict:
    _ = current_user
    mapping = map_route_to_skill(route_category)
    skill = get_skill(mapping.skill_code) if mapping.skill_code else None
    return {
        "mapping": mapping.model_dump(mode="json"),
        "skill": skill.model_dump(mode="json") if skill else None,
        "execution_enabled": False,
    }


@router.get("/{skill_code}/clarification")
async def skill_clarification(
    skill_code: SpecialistSkillCode,
    current_user: UserTable = Depends(require_active_user),
) -> dict:
    _ = current_user
    skill = get_skill(skill_code)
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    empty = evaluate_clarification(skill_code, {})
    return {
        "skill": skill.model_dump(mode="json"),
        "clarification_schema": skill.clarification_schema,
        "empty_input_result": empty.model_dump(mode="json"),
        "execution_enabled": False,
    }


@router.get("/{skill_code}/allowed")
async def skill_allowed(
    skill_code: SpecialistSkillCode,
    specialist_role: str = Query(...),
    current_user: UserTable = Depends(require_active_user),
) -> dict:
    _ = current_user
    return {
        "specialist_role": specialist_role,
        "skill_code": skill_code.value,
        "allowed": skill_allowed_for_specialist(specialist_role, skill_code),
    }
