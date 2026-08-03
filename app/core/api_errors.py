"""HTTP exception handlers and request id middleware (Phase AI.88)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import (
    ApiClientError,
    BetaAccessDeniedError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    OwnershipError,
    RateLimitExceededError,
)
from app.schemas.api_errors import ApiErrorResponse


def _request_id(request: Request) -> str:
    existing = getattr(request.state, "request_id", None)
    if isinstance(existing, str) and existing:
        return existing
    return str(uuid.uuid4())


def _envelope(
    *,
    error_code: str,
    safe_message: str,
    request: Request,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = ApiErrorResponse(
        error_code=error_code,
        safe_message=safe_message,
        details=details or {},
        request_id=_request_id(request),
    )
    return body.model_dump(mode="json")


_STABLE_DOMAIN_ERROR_CODES: dict[str, str] = {
    "long_form_requires_plan_preview": (
        "Long-form video requires a scene plan. Prepare a plan in Video Studio before generating."
    ),
    "unsupported_video_duration": "The requested video duration is not supported.",
    "unsupported_aspect_ratio": "The requested aspect ratio is not supported.",
    "unsupported_camera_movement": "The selected camera movement is not supported.",
    "aspect_ratio_unavailable": "The selected aspect ratio is not available on the current pipeline.",
    "start_end_frame_not_available": "Start/end frame mode is not available yet.",
    "source_asset_not_found": "The source image was not found.",
    "source_asset_file_missing": "The source image file is missing.",
    "source_asset_not_image": "The source asset is not an image.",
    "source_asset_not_ready": "The source image is not ready for video generation.",
    "source_asset_not_accepted": "The source image must be accepted before animating.",
    "source_asset_identity_reference_blocked": (
        "Identity reference images cannot be used as video source frames."
    ),
    "clip_request_not_in_preview": "This clip request is no longer in preview state.",
    "clip_request_not_reconcilable": "This clip request cannot be reconciled in its current state.",
    "reconcile_requires_provider_job_id": (
        "Cannot reconcile without a provider job id on this request."
    ),
    "approval_required": "Explicit approval is required before generating video.",
    "idempotency_key_required": "Idempotency-Key header is required for paid generation.",
    "quote_mismatch": "The quote does not match the current research request.",
    "quote_expired": "The cost quote has expired. Request a new quote.",
    "quote_required": "A cost quote is required before approval.",
    "preflight_required": "Preflight checks must complete before requesting a quote.",
    "preflight_not_ready": "Research preflight is not ready yet.",
    "approval_expired": "The approval has expired. Confirm again after a new quote.",
    "approval_invalid": "The approval is not valid for this research run.",
    "approval_quote_mismatch": "The approval does not match the active quote.",
    "approval_request_hash_mismatch": "The approval does not match the current request.",
    "execution_not_enabled_in_phase_1b_1": (
        "Paid research execution is not enabled in Phase 1B.1."
    ),
    "outcome_unknown_no_blind_retry": (
        "The previous paid operation outcome is unknown; blind retry is blocked."
    ),
    "retry_not_allowed": "Retry is not allowed for this research run.",
    "commercial_research_run_not_found": "Commercial research run was not found.",
    "analysis_context_required": "Подтвердите данные перед запуском анализа.",
    "hydrated_context_confirmation_required": "Подтвердите восстановленные данные проекта.",
    "analysis_context_incomplete": "Не хватает данных для анализа.",
    "analysis_context_stale": "Данные изменились — подтвердите заново.",
    "analysis_context_not_found": "Контекст анализа не найден.",
    "invalid_analysis_context_state": "Нельзя запустить анализ в текущем состоянии.",
    "research_idempotency_key_required": (
        "Не удалось запустить исследование. Попробуйте повторить запуск."
    ),
    "rerun_idempotency_key_required": (
        "Не удалось повторно запустить исследование. Попробуйте ещё раз."
    ),
    "idempotency_key_required": "Не удалось запустить операцию. Обновите страницу и попробуйте снова.",
    "business_idea_validation_disabled": "Проверка идей временно недоступна.",
    "mcp_disabled": "Сервис исследования временно недоступен.",
    "not_configured": "Сервис исследования не настроен.",
    "pipeline_fetch_zero_success": (
        "Поиск нашёл источники, но ни одна страница не была успешно загружена. "
        "Исследование не может быть завершено без документов."
    ),
    "pipeline_extraction_zero_success": (
        "Страницы загружены, но текст не удалось извлечь для анализа."
    ),
    "research_execution_interrupted": (
        "Исследование было прервано. Запустите проверку идеи повторно."
    ),
    "investigation_immutable": (
        "Исследование было прервано из-за конфликта состояния. Запустите проверку повторно."
    ),
    "active_research_run_exists": (
        "Исследование уже выполняется для этого проекта. Дождитесь завершения или откройте проект снова."
    ),
}


def _map_domain_message(message: str) -> tuple[str, str]:
    if message in _STABLE_DOMAIN_ERROR_CODES:
        return message, _STABLE_DOMAIN_ERROR_CODES[message]
    lowered = message.lower()
    if "not found" in lowered:
        return "not_found", "The requested resource was not found."
    if "not enabled" in lowered or "not allowed" in lowered:
        return "not_allowed", message
    if "limit" in lowered or "maximum" in lowered:
        return "limit_exceeded", message
    return "invalid_state", message


def _sanitize_correlation_id(raw: str | None) -> str:
    """Accept inbound correlation/request id or generate; bound length; strip unsafe chars."""
    import re

    if not raw:
        return str(uuid.uuid4())
    cleaned = re.sub(r"[^A-Za-z0-9._\-]", "", raw.strip())[:128]
    return cleaned or str(uuid.uuid4())


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("X-Request-ID") or request.headers.get(
            "X-Correlation-ID"
        )
        request_id = _sanitize_correlation_id(incoming)
        request.state.request_id = request_id
        request.state.correlation_id = request_id
        try:
            import structlog

            structlog.contextvars.clear_contextvars()
            structlog.contextvars.bind_contextvars(
                correlation_id=request_id,
                request_id=request_id,
                http_method=request.method,
                http_path=request.url.path,
            )
        except Exception:  # noqa: BLE001 — logging must not break requests
            pass
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = request_id
        return response


def register_api_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(BetaAccessDeniedError)
    async def beta_access_handler(
        request: Request,
        exc: BetaAccessDeniedError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content=_envelope(
                error_code=exc.error_code,
                safe_message=exc.safe_message,
                request=request,
            ),
        )

    @application.exception_handler(RateLimitExceededError)
    async def rate_limit_handler(
        request: Request,
        exc: RateLimitExceededError,
    ) -> JSONResponse:
        details: dict[str, Any] = {}
        if exc.limit is not None:
            details["limit"] = exc.limit
        return JSONResponse(
            status_code=429,
            content=_envelope(
                error_code=exc.error_code,
                safe_message=exc.safe_message,
                request=request,
                details=details,
            ),
        )

    @application.exception_handler(ApiClientError)
    async def api_client_handler(request: Request, exc: ApiClientError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(
                error_code=exc.error_code,
                safe_message=exc.safe_message,
                request=request,
                details=exc.details,
            ),
        )

    @application.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=_envelope(
                error_code="not_found",
                safe_message="The requested resource was not found.",
                request=request,
            ),
        )

    @application.exception_handler(OwnershipError)
    async def ownership_handler(request: Request, exc: OwnershipError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=_envelope(
                error_code="not_found",
                safe_message="The requested resource was not found.",
                request=request,
            ),
        )

    @application.exception_handler(InvalidStateError)
    async def invalid_state_handler(request: Request, exc: InvalidStateError) -> JSONResponse:
        code, message = _map_domain_message(str(exc))
        return JSONResponse(
            status_code=409,
            content=_envelope(
                error_code=code,
                safe_message=message,
                request=request,
            ),
        )

    @application.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
        code, message = _map_domain_message(str(exc))
        return JSONResponse(
            status_code=409,
            content=_envelope(
                error_code=code,
                safe_message=message,
                request=request,
            ),
        )

    @application.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict):
            error_code = str(detail.get("error_code", "http_error"))
            safe_message = str(detail.get("safe_message", detail.get("detail", "Request failed")))
            extra_details = {
                k: v
                for k, v in detail.items()
                if k not in {"error_code", "safe_message", "detail"}
            }
        else:
            safe_message = str(detail)
            error_code = "not_found" if exc.status_code == 404 else "http_error"
            if exc.status_code in {401, 403} and isinstance(detail, str) and detail:
                # Preserve stable auth error codes for browser clients (CPH.3).
                error_code = detail
                safe_message = detail
            elif safe_message in _STABLE_DOMAIN_ERROR_CODES:
                error_code = safe_message
                safe_message = _STABLE_DOMAIN_ERROR_CODES[safe_message]
            elif exc.status_code == 409:
                error_code, safe_message = _map_domain_message(safe_message)
            elif exc.status_code == 429:
                error_code = "rate_limit_exceeded"
            extra_details = {}
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(
                error_code=error_code,
                safe_message=safe_message,
                request=request,
                details=extra_details,
            ),
        )

    @application.exception_handler(RequestValidationError)
    async def validation_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_envelope(
                error_code="validation_error",
                safe_message="Request validation failed.",
                request=request,
                details={"errors": exc.errors()},
            ),
        )

    @application.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=_envelope(
                error_code="internal_error",
                safe_message="An unexpected error occurred. Please try again later.",
                request=request,
            ),
        )
