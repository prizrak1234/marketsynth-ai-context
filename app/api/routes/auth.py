"""Auth API routes — API keys + pilot browser sessions (CPH.3)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_role
from app.api.deps import get_session
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models.user import UserTable
from app.domain.email_normalize import is_valid_email, normalize_email
from app.domain.login_rate_limit import (
    clear_login_failures,
    is_login_rate_limited,
    record_login_failure,
)
from app.schemas.auth import (
    ApiKeyCreatedResponse,
    ApiKeyCreateRequest,
    ApiKeyListItem,
    AuthMeResponse,
    BrowserLoginRequest,
    BrowserLoginResponse,
    BrowserSessionListItem,
    ChangePasswordRequest,
    ChangePasswordResponse,
    PasswordResetCompleteRequest,
    PasswordResetCompleteResponse,
    PasswordResetRequestBody,
    PasswordResetRequestResponse,
    PasswordResetStatusResponse,
    PilotInviteAcceptRequest,
    PilotInviteAcceptResponse,
    PilotInviteCreateRequest,
    PilotInviteCreateResponse,
    PilotInviteStatusResponse,
    RegisterRequest,
    RegisterResponse,
    SignupStatusResponse,
)
from app.schemas.contracts import BrowserSessionStatus, UserRole
from app.services.auth import AuthService
from app.services.browser_session_service import BrowserSessionService
from app.services.password_reset_service import PasswordResetError, PasswordResetService
from app.services.pilot_invite_service import PilotInviteError, PilotInviteService
from app.services.registration_service import RegistrationError, RegistrationService

router = APIRouter(prefix="/auth", tags=["auth"])
log = get_logger(__name__)


def _set_session_cookie(response: Response, plain_token: str, max_age: int) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.browser_session_cookie_name,
        value=plain_token,
        max_age=max_age,
        path="/",
        httponly=True,
        secure=settings.browser_session_cookie_secure,
        samesite=settings.browser_session_cookie_samesite,
    )


def _clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.browser_session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.browser_session_cookie_secure,
        samesite=settings.browser_session_cookie_samesite,
    )


def _me(user: UserTable) -> AuthMeResponse:
    return AuthMeResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
    )


@router.post("/login", response_model=BrowserLoginResponse)
async def browser_login(
    body: BrowserLoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> BrowserLoginResponse:
    settings = get_settings()
    email = normalize_email(body.email)
    if not is_valid_email(email):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_credentials",
        )
    client_host = request.client.host if request.client else "unknown"
    rate_key = f"{client_host}:{email}"
    if is_login_rate_limited(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="rate_limited",
        )

    service = BrowserSessionService(session)
    result = await service.login(
        email=email,
        password=body.password,
        user_agent=request.headers.get("user-agent"),
    )
    if result is None:
        record_login_failure(rate_key)
        # Non-enumerating generic failure
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_credentials",
        )
    clear_login_failures(rate_key)
    ttl_seconds = int(settings.browser_session_ttl_hours * 3600)
    _set_session_cookie(response, result.plain_token, ttl_seconds)
    return BrowserLoginResponse(
        user=_me(result.user),
        session_id=result.session.id,
        expires_at=result.session.expires_at,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def browser_logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> None:
    settings = get_settings()
    token = request.cookies.get(settings.browser_session_cookie_name)
    if token:
        await BrowserSessionService(session).revoke_token(token, reason="logout")
    _clear_session_cookie(response)


@router.get("/me", response_model=AuthMeResponse)
async def auth_me(
    current_user: UserTable = Depends(require_active_user),
) -> AuthMeResponse:
    return _me(current_user)


@router.get("/signup-status", response_model=SignupStatusResponse)
async def signup_status() -> SignupStatusResponse:
    settings = get_settings()
    return SignupStatusResponse(
        signup_enabled=settings.signup_enabled,
        invite_activation_available=True,
    )


def _registration_http_error(exc: RegistrationError) -> HTTPException:
    code = exc.code
    if code == "signup_disabled":
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=code)
    if code == "email_taken":
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=code)
    if code in {
        "password_mismatch",
        "password_too_short",
        "password_too_weak",
        "display_name_required",
        "notice_required",
        "invalid_email",
        "current_password_invalid",
    }:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> RegisterResponse:
    client_host = request.client.host if request.client else "unknown"
    email_probe = normalize_email(body.email)
    rate_key = f"register:{client_host}:{email_probe}"
    if is_login_rate_limited(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="rate_limited",
        )
    service = RegistrationService(session)
    try:
        result = await service.register(
            email=body.email,
            display_name=body.display_name,
            password=body.password,
            password_confirm=body.password_confirmation,
            accept_notice=body.accepted_pilot_notice,
            user_agent=request.headers.get("user-agent"),
        )
    except RegistrationError as exc:
        record_login_failure(rate_key)
        raise _registration_http_error(exc) from exc
    clear_login_failures(rate_key)
    settings = get_settings()
    ttl_seconds = int(settings.browser_session_ttl_hours * 3600)
    _set_session_cookie(response, result.plain_token, ttl_seconds)
    return RegisterResponse(
        user=_me(result.user),
        session_id=result.session.id,
        expires_at=result.session.expires_at,
    )


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ChangePasswordResponse:
    session_id_raw = getattr(request.state, "ms_auth_session_id", None)
    current_session_id: UUID | None = None
    if session_id_raw:
        try:
            current_session_id = UUID(str(session_id_raw))
        except ValueError:
            current_session_id = None
    service = RegistrationService(session)
    try:
        revoked = await service.change_password(
            user=current_user,
            current_password=body.current_password,
            new_password=body.new_password,
            new_password_confirm=body.new_password_confirmation,
            current_session_id=current_session_id,
        )
    except RegistrationError as exc:
        raise _registration_http_error(exc) from exc
    return ChangePasswordResponse(ok=True, revoked_other_sessions=revoked)


GENERIC_RESET_MESSAGE = (
    "If an account exists, password reset instructions have been created."
)


def _reset_http_error(exc: PasswordResetError) -> HTTPException:
    code = exc.code
    if code in {
        "token_expired",
        "token_revoked",
        "token_used",
        "invalid_token",
        "password_mismatch",
        "password_too_short",
        "password_too_weak",
    }:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code)


@router.post("/password-reset/request", response_model=PasswordResetRequestResponse)
async def password_reset_request(
    body: PasswordResetRequestBody,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> PasswordResetRequestResponse:
    """Always generic — never reveal whether the email exists or return a token."""
    client_host = request.client.host if request.client else "unknown"
    email_n = normalize_email(body.email) if body.email else ""
    rate_key = f"pw-reset:{client_host}:{email_n or 'invalid'}"
    if is_login_rate_limited(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="rate_limited",
        )
    # Throttle enumeration / flooding; still return the same message.
    record_login_failure(rate_key)
    if is_valid_email(email_n):
        await PasswordResetService(session).request_reset(
            email=email_n,
            client_ip=client_host,
            user_agent=request.headers.get("user-agent"),
        )
    return PasswordResetRequestResponse(message=GENERIC_RESET_MESSAGE)


@router.get(
    "/password-reset/{token}/status",
    response_model=PasswordResetStatusResponse,
)
async def password_reset_status(
    token: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> PasswordResetStatusResponse:
    client_host = request.client.host if request.client else "unknown"
    rate_key = f"pw-reset-status:{client_host}"
    if is_login_rate_limited(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="rate_limited",
        )
    view = await PasswordResetService(session).status_for_token(token)
    if view.state.value == "invalid":
        record_login_failure(rate_key)
    return PasswordResetStatusResponse(state=view.state.value)


@router.post(
    "/password-reset/{token}/complete",
    response_model=PasswordResetCompleteResponse,
)
async def password_reset_complete(
    token: str,
    body: PasswordResetCompleteRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> PasswordResetCompleteResponse:
    client_host = request.client.host if request.client else "unknown"
    rate_key = f"pw-reset-complete:{client_host}"
    if is_login_rate_limited(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="rate_limited",
        )
    try:
        await PasswordResetService(session).complete(
            raw_token=token,
            new_password=body.password,
            new_password_confirm=body.password_confirmation,
        )
    except PasswordResetError as exc:
        record_login_failure(rate_key)
        raise _reset_http_error(exc) from exc
    clear_login_failures(rate_key)
    return PasswordResetCompleteResponse(ok=True)


@router.get("/sessions", response_model=list[BrowserSessionListItem])
async def list_sessions(
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> list[BrowserSessionListItem]:
    rows = await BrowserSessionService(session).list_sessions(current_user.id)
    return [
        BrowserSessionListItem(
            id=r.id,
            status=BrowserSessionStatus(r.status),
            purpose=r.purpose,
            created_at=r.created_at,
            expires_at=r.expires_at,
            last_seen_at=r.last_seen_at,
            revoked_at=r.revoked_at,
        )
        for r in rows
    ]


@router.post("/sessions/{session_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> None:
    revoked = await BrowserSessionService(session).revoke_session(
        session_id, current_user.id, reason="user_revoke"
    )
    if revoked is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_not_found")


@router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: ApiKeyCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ApiKeyCreatedResponse:
    auth_service = AuthService(session)
    created = await auth_service.create_api_key(current_user.id, body.name)
    return ApiKeyCreatedResponse(
        id=created.api_key.id,
        name=created.api_key.name,
        key_prefix=created.api_key.key_prefix,
        api_key=created.plain_key,
    )


@router.get("/api-keys", response_model=list[ApiKeyListItem])
async def list_api_keys(
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> list[ApiKeyListItem]:
    auth_service = AuthService(session)
    rows = await auth_service.list_api_keys(current_user.id)
    return [
        ApiKeyListItem(
            id=row.id,
            name=row.name,
            key_prefix=row.key_prefix,
            is_active=row.is_active,
            created_at=row.created_at,
            last_used_at=row.last_used_at,
            revoked_at=row.revoked_at,
        )
        for row in rows
    ]


@router.delete("/api-keys/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    api_key_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> None:
    auth_service = AuthService(session)
    revoked = await auth_service.revoke_api_key(api_key_id, current_user.id)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )


def _activation_base_url() -> str:
    settings = get_settings()
    if settings.public_frontend_url:
        return settings.public_frontend_url.rstrip("/")
    origins = settings.browser_allowed_origins or []
    for preferred in ("http://localhost:3000", "http://127.0.0.1:3000"):
        if preferred in origins:
            return preferred
    if origins:
        return origins[0].rstrip("/")
    return "http://localhost:3000"


def _invite_http_error(exc: PilotInviteError) -> HTTPException:
    code = exc.code
    if code == "account_exists":
        # Non-enumerating guidance once they hold a token/email path
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="account_exists",
        )
    if code in {"pending_invite_exists"}:
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=code)
    if code in {
        "invite_expired",
        "invite_revoked",
        "invite_used",
        "invalid_token",
        "invite_not_pending",
    }:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code)
    if code in {
        "password_mismatch",
        "password_too_short",
        "password_too_weak",
        "display_name_required",
        "notice_required",
        "invalid_email",
        "invalid_ttl",
    }:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code)


@router.post(
    "/invitations",
    response_model=PilotInviteCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    body: PilotInviteCreateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(
        require_role(UserRole.OWNER, UserRole.ADMIN)
    ),
) -> PilotInviteCreateResponse:
    service = PilotInviteService(session)
    try:
        result = await service.create_invite(
            email=body.email,
            created_by_user_id=current_user.id,
            ttl_hours=body.ttl_hours,
            replace_pending=body.replace_pending,
        )
    except PilotInviteError as exc:
        raise _invite_http_error(exc) from exc
    activation_url = f"{_activation_base_url()}/activate-invite?token={result.plain_token}"
    # Never log plain token
    log.info(
        "pilot_invite_api_created",
        invite_id=str(result.invite.id),
        actor_user_id=str(current_user.id),
        client=(request.client.host if request.client else None),
    )
    return PilotInviteCreateResponse(
        invite_id=result.invite.id,
        email=result.invite.email_normalized,
        expires_at=result.invite.expires_at,
        activation_url=activation_url,
        token=result.plain_token,
    )


@router.get("/invitations/{token}/status", response_model=PilotInviteStatusResponse)
async def invitation_status(
    token: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> PilotInviteStatusResponse:
    client_host = request.client.host if request.client else "unknown"
    rate_key = f"invite-status:{client_host}"
    if is_login_rate_limited(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="rate_limited",
        )
    service = PilotInviteService(session)
    view = await service.status_for_token(token)
    if view.state.value == "invalid":
        record_login_failure(rate_key)
    return PilotInviteStatusResponse(
        state=view.state.value,
        email=view.email,
        expires_at=view.expires_at,
    )


@router.post("/invitations/{token}/accept", response_model=PilotInviteAcceptResponse)
async def accept_invitation(
    token: str,
    body: PilotInviteAcceptRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> PilotInviteAcceptResponse:
    client_host = request.client.host if request.client else "unknown"
    rate_key = f"invite-accept:{client_host}"
    if is_login_rate_limited(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="rate_limited",
        )
    service = PilotInviteService(session)
    try:
        result = await service.accept(
            raw_token=token,
            display_name=body.display_name,
            password=body.password,
            password_confirm=body.password_confirm,
            accept_notice=body.accept_pilot_notice,
            user_agent=request.headers.get("user-agent"),
        )
    except PilotInviteError as exc:
        record_login_failure(rate_key)
        raise _invite_http_error(exc) from exc
    clear_login_failures(rate_key)
    settings = get_settings()
    ttl_seconds = int(settings.browser_session_ttl_hours * 3600)
    _set_session_cookie(response, result.plain_token, ttl_seconds)
    return PilotInviteAcceptResponse(
        user=_me(result.user),
        session_id=result.session.id,
        expires_at=result.session.expires_at,
    )


@router.post("/invitations/{invite_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    invite_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(
        require_role(UserRole.OWNER, UserRole.ADMIN)
    ),
) -> None:
    service = PilotInviteService(session)
    try:
        revoked = await service.revoke(invite_id, actor_user_id=current_user.id)
    except PilotInviteError as exc:
        raise _invite_http_error(exc) from exc
    if revoked is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invite_not_found")
