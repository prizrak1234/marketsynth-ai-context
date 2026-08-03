"""Auth skeleton tests."""

from __future__ import annotations

import asyncio

import pytest
from app.api.dependencies.auth import require_role
from app.db.models.user import UserTable
from app.schemas.contracts import UserRole
from app.schemas.crud import UserCreate
from app.security.auth import generate_api_key, hash_api_key, verify_api_key
from app.services.auth import AuthService
from app.services.users_service import UserService
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import _create_user_with_api_key


def test_generate_api_key_returns_hash_and_prefix() -> None:
    plain_key, prefix, key_hash = generate_api_key()
    assert plain_key.startswith("bfz_")
    assert plain_key.startswith(prefix)
    assert verify_api_key(plain_key, key_hash)
    assert hash_api_key(plain_key) == key_hash


@pytest.mark.asyncio
async def test_create_api_key_returns_plain_once(db_session: AsyncSession) -> None:
    user = await UserService(db_session).create(UserCreate(telegram_id=5001))
    created = await AuthService(db_session).create_api_key(user.id, "dev")
    assert created.plain_key.startswith("bfz_")
    assert created.api_key.key_hash != created.plain_key
    assert created.api_key.key_prefix in created.plain_key


@pytest.mark.asyncio
async def test_authenticate_api_key_valid(db_session: AsyncSession) -> None:
    user = await UserService(db_session).create(UserCreate(telegram_id=5002))
    auth_service = AuthService(db_session)
    created = await auth_service.create_api_key(user.id, "valid")
    result = await auth_service.authenticate_api_key(created.plain_key)
    assert result is not None
    authenticated_user, api_key = result
    assert authenticated_user.id == user.id
    assert api_key.id == created.api_key.id


@pytest.mark.asyncio
async def test_authenticate_api_key_invalid(db_session: AsyncSession) -> None:
    assert await AuthService(db_session).authenticate_api_key("bfz_invalid") is None


@pytest.mark.asyncio
async def test_revoked_api_key_is_rejected(db_session: AsyncSession) -> None:
    user = await UserService(db_session).create(UserCreate(telegram_id=5003))
    auth_service = AuthService(db_session)
    created = await auth_service.create_api_key(user.id, "revoke-me")
    revoked = await auth_service.revoke_api_key(created.api_key.id, user.id)
    assert revoked is True
    assert await auth_service.authenticate_api_key(created.plain_key) is None


def test_valid_bearer_key_allows_access(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/projects", headers=auth_headers)
    assert response.status_code == 200


def test_invalid_bearer_key_returns_401(client: TestClient) -> None:
    response = client.get("/projects", headers={"Authorization": "Bearer bfz_invalid"})
    assert response.status_code == 401


def test_revoked_key_returns_401(client: TestClient, database_url: str) -> None:
    plain_key, user = asyncio.run(_create_user_with_api_key(telegram_id=5004))

    async def _revoke() -> None:
        from app.db.session import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            auth_service = AuthService(session)
            keys = await auth_service.list_api_keys(user.id)
            await auth_service.revoke_api_key(keys[0].id, user.id)

    asyncio.run(_revoke())
    response = client.get("/projects", headers={"Authorization": f"Bearer {plain_key}"})
    assert response.status_code == 401


def test_user_cannot_access_other_users_project(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "Private"},
        headers=auth_headers,
    ).json()["id"]

    assert client.get(f"/projects/{project_id}", headers=other_auth_headers).status_code == 404
    assert (
        client.patch(
            f"/projects/{project_id}",
            json={"name": "Hacked"},
            headers=other_auth_headers,
        ).status_code
        == 404
    )
    assert client.delete(f"/projects/{project_id}", headers=other_auth_headers).status_code == 404


def test_inactive_user_returns_403(client: TestClient, database_url: str) -> None:
    plain_key, _user = asyncio.run(_create_user_with_api_key(telegram_id=5005, is_active=False))
    response = client.get("/projects", headers={"Authorization": f"Bearer {plain_key}"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_require_role_blocks_unauthorized_role() -> None:
    checker = require_role(UserRole.ADMIN, UserRole.OWNER)
    member = UserTable(role=UserRole.MEMBER, is_active=True)
    with pytest.raises(HTTPException) as exc:
        await checker(current_user=member)
    assert exc.value.status_code == 403


def test_create_api_key_via_api(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/auth/api-keys",
        json={"name": "Cursor dev key"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["api_key"].startswith("bfz_")
    assert "key_prefix" in body

    listed = client.get("/auth/api-keys", headers=auth_headers)
    assert listed.status_code == 200
    assert any(item["name"] == "Cursor dev key" for item in listed.json())
    assert all("api_key" not in item for item in listed.json())
