"""Resilient multi-provider fetch orchestration with ledger persistence."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.business_idea_validation.content_extraction import (
    ContentExtractionResult,
    ExtractionRunContext,
    ExtractionStatus,
    extract_and_normalize_document,
    rejection_to_fetch_outcome,
)
from app.business_idea_validation.fetch_circuit_breaker import get_fetch_circuit_registry
from app.business_idea_validation.fetch_outcomes import (
    map_business_tool_error,
    map_exception,
    safe_error_message,
)
from app.business_idea_validation.pipeline_metrics import BivPipelineMetricsRecorder
from app.business_idea_validation.research_fetch.mapping import status_to_outcome
from app.business_idea_validation.research_fetch.policy import (
    is_fallback_eligible,
    max_provider_attempts,
    parse_provider_order,
)
from app.business_idea_validation.research_fetch.port import (
    FetchAttemptLineage,
    FetchRequest,
    ResearchFetchStatus,
)
from app.business_idea_validation.research_fetch.registry import build_fetch_adapters
from app.business_idea_validation.research_fetch.security import validate_fetch_url
from app.business_tools.contracts import BusinessToolError, SourceCandidate, SourceFetchResult
from app.business_tools.providers.firecrawl_fetch import FirecrawlFetchTool
from app.core.config import Settings
from app.db.base import utc_now
from app.db.models.biv_fetch_ledger import BivFetchLedgerTable
from app.db.repositories.biv_fetch_ledger import BivFetchLedgerRepository
from app.domain.source_fingerprint import normalize_url
from app.schemas.contracts import BivFetchOutcomeCode


@dataclass(slots=True)
class FetchOrchestratorResult:
    success: bool
    url: str
    normalized_url: str
    outcome: BivFetchOutcomeCode
    fetch_result: SourceFetchResult | None
    audit_id: UUID | None
    extracted_text: str
    title: str | None
    fallback_used: bool
    extraction: ContentExtractionResult | None = None
    provider: str | None = None
    attempt_lineage: list[FetchAttemptLineage] = field(default_factory=list)


class BivFetchOrchestrator:
    PROVIDER_FIRECRAWL = "firecrawl"
    PROVIDER_DIRECT_HTTP = "direct_http"
    PROVIDER_TRAFILATURA = "trafilatura"

    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        *,
        run_id: UUID,
        correlation_id: str,
        metrics: BivPipelineMetricsRecorder | None = None,
        tenant_id: str | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._run_id = run_id
        self._correlation_id = correlation_id
        self._tenant_id = tenant_id
        self._ledger = BivFetchLedgerRepository(session)
        self._firecrawl = FirecrawlFetchTool(settings)
        self._circuits = get_fetch_circuit_registry()
        self._metrics = metrics
        self._attempts_for_url: dict[str, int] = {}
        self._total_attempts = 0
        self._extraction_ctx = ExtractionRunContext()
        self._normalized_documents: list[ContentExtractionResult] = []
        self._success_cache: dict[str, FetchOrchestratorResult] = {}
        self._adapters = build_fetch_adapters(settings)
        self._lineage: list[FetchAttemptLineage] = []

    @property
    def normalized_documents(self) -> list[ContentExtractionResult]:
        return list(self._normalized_documents)

    async def fetch_url(
        self,
        url: str,
        *,
        query_id: str = "",
        mcp_fetch=None,
    ) -> FetchOrchestratorResult:
        self._lineage = []
        normalized = normalize_url(url) or url.strip()
        safe, unsafe_code = validate_fetch_url(normalized)
        if not normalized.startswith("http") or not safe:
            outcome = (
                BivFetchOutcomeCode.UNSAFE_URL
                if unsafe_code == "unsafe_url"
                else BivFetchOutcomeCode.MALFORMED_CONTENT
            )
            await self._record_attempt(
                url=url,
                normalized_url=normalized,
                query_id=query_id,
                provider="none",
                attempt_number=1,
                outcome=outcome,
                http_status=None,
                content_type=None,
                content_length=0,
                extracted_len=0,
                retryable=False,
                fallback_used=False,
                error_class=unsafe_code or "InvalidURL",
                safe_msg=safe_error_message(outcome),
                started=utc_now(),
            )
            return FetchOrchestratorResult(
                success=False,
                url=url,
                normalized_url=normalized,
                outcome=outcome,
                fetch_result=None,
                audit_id=None,
                extracted_text="",
                title=None,
                fallback_used=False,
            )

        if (
            self._settings.research_fetch_cache_enabled
            and normalized in self._success_cache
        ):
            cached = self._success_cache[normalized]
            await self._record_attempt(
                url=url,
                normalized_url=normalized,
                query_id=query_id,
                provider="cache",
                attempt_number=self._next_attempt(normalized),
                outcome=BivFetchOutcomeCode.DUPLICATE_URL,
                http_status=None,
                content_type=None,
                content_length=0,
                extracted_len=len(cached.extracted_text),
                retryable=False,
                fallback_used=False,
                error_class="duplicate_url",
                safe_msg=safe_error_message(BivFetchOutcomeCode.DUPLICATE_URL),
                started=utc_now(),
            )
            if self._metrics:
                self._metrics.record_fetch_attempt(
                    BivFetchOutcomeCode.DUPLICATE_URL,
                    normalized_url=normalized,
                )
            return cached

        if self._total_attempts >= self._settings.biv_max_total_fetch_attempts:
            outcome = BivFetchOutcomeCode.CANCELLED
            await self._record_attempt(
                url=url,
                normalized_url=normalized,
                query_id=query_id,
                provider="none",
                attempt_number=1,
                outcome=outcome,
                http_status=None,
                content_type=None,
                content_length=0,
                extracted_len=0,
                retryable=False,
                fallback_used=False,
                error_class="BudgetExceeded",
                safe_msg="Fetch budget exhausted.",
                started=utc_now(),
            )
            return FetchOrchestratorResult(
                success=False,
                url=url,
                normalized_url=normalized,
                outcome=outcome,
                fetch_result=None,
                audit_id=None,
                extracted_text="",
                title=None,
                fallback_used=False,
            )

        if self._metrics:
            self._metrics.record_fetch_eligible()

        provider_order = parse_provider_order(self._settings)
        if not self._settings.research_fetch_fallback_enabled:
            provider_order = provider_order[:1]

        last_outcome = BivFetchOutcomeCode.UNKNOWN_ERROR
        last_error_class: str | None = None
        fallback_used = False
        attempts_budget = max_provider_attempts(self._settings)
        provider_steps = 0

        for idx, provider_name in enumerate(provider_order):
            if provider_steps >= attempts_budget:
                break
            is_fallback = idx > 0
            circuit = self._circuits.get(provider_name)
            if not circuit.allow_request():
                continue

            if provider_name == self.PROVIDER_FIRECRAWL:
                if is_fallback:
                    await asyncio.sleep(self._backoff_delay(attempt=2))
                started = utc_now()
                attempt_num = self._next_attempt(normalized)
                provider_steps += 1
                try:
                    result = await self._fetch_firecrawl(
                        normalized,
                        mcp_fetch=mcp_fetch,
                        started=started,
                        query_id=query_id,
                        url_original=url,
                        is_fallback=is_fallback,
                    )
                except Exception as exc:  # noqa: BLE001
                    outcome, err_class, safe_msg = map_exception(exc)
                    await self._record_attempt(
                        url=url,
                        normalized_url=normalized,
                        query_id=query_id,
                        provider=provider_name,
                        attempt_number=attempt_num,
                        outcome=outcome,
                        http_status=None,
                        content_type=None,
                        content_length=0,
                        extracted_len=0,
                        retryable=is_fallback_eligible(outcome, error_class=err_class),
                        fallback_used=is_fallback,
                        error_class=err_class,
                        safe_msg=safe_msg,
                        started=started,
                    )
                    self._append_lineage(provider_name, outcome, err_class)
                    circuit.record_failure()
                    last_outcome = outcome
                    last_error_class = err_class
                    if not is_fallback_eligible(outcome, error_class=err_class):
                        break
                    fallback_used = is_fallback
                    continue

                outcome, fetch_result, audit_id, text, title, http_status, content_type = result
                if outcome == BivFetchOutcomeCode.SUCCESS:
                    circuit.record_success()
                    final = self._success_result(
                        url=url,
                        normalized=normalized,
                        outcome=outcome,
                        fetch_result=fetch_result,
                        audit_id=audit_id,
                        text=text,
                        title=title,
                        fallback_used=is_fallback,
                        provider=provider_name,
                    )
                    self._cache_success(normalized, final)
                    return final

                circuit.record_failure()
                last_outcome = outcome
                last_error_class = (
                    "credits_exhausted"
                    if outcome == BivFetchOutcomeCode.CREDITS_EXHAUSTED
                    else "ExtractReject"
                )
                self._append_lineage(provider_name, outcome, last_error_class)
                if not is_fallback_eligible(outcome, error_class=last_error_class):
                    break
                fallback_used = is_fallback
                continue

            adapter = self._adapters.get(provider_name)
            if adapter is None or not adapter.is_available():
                continue

            started = utc_now()
            attempt_num = self._next_attempt(normalized)
            provider_steps += 1
            req = FetchRequest(
                tenant_id=self._tenant_id,
                research_run_id=self._run_id,
                source_url=url,
                normalized_url=normalized,
                requested_at=started,
                timeout_seconds=self._settings.research_fetch_timeout_seconds,
                max_content_bytes=self._settings.research_fetch_max_content_bytes,
                trace_context={"attempt_number": str(attempt_num)},
            )
            try:
                domain_result = await adapter.fetch(req)
            except BusinessToolError as exc:
                outcome = map_business_tool_error(exc.category)
                await self._record_attempt(
                    url=url,
                    normalized_url=normalized,
                    query_id=query_id,
                    provider=provider_name,
                    attempt_number=attempt_num,
                    outcome=outcome,
                    http_status=None,
                    content_type=None,
                    content_length=0,
                    extracted_len=0,
                    retryable=is_fallback_eligible(outcome, error_class=exc.category),
                    fallback_used=is_fallback,
                    error_class=exc.category,
                    safe_msg=(exc.user_message or str(exc))[:500],
                    started=started,
                )
                self._append_lineage(provider_name, outcome, exc.category)
                circuit.record_failure()
                last_outcome = outcome
                last_error_class = exc.category
                if self._metrics:
                    self._metrics.record_fetch_fallback(provider_name, exc.category)
                if not is_fallback_eligible(outcome, error_class=exc.category):
                    break
                fallback_used = is_fallback
                continue
            except Exception as exc:  # noqa: BLE001
                outcome, err_class, safe_msg = map_exception(exc)
                await self._record_attempt(
                    url=url,
                    normalized_url=normalized,
                    query_id=query_id,
                    provider=provider_name,
                    attempt_number=attempt_num,
                    outcome=outcome,
                    http_status=None,
                    content_type=None,
                    content_length=0,
                    extracted_len=0,
                    retryable=is_fallback_eligible(outcome, error_class=err_class),
                    fallback_used=is_fallback,
                    error_class=err_class,
                    safe_msg=safe_msg,
                    started=started,
                )
                self._append_lineage(provider_name, outcome, err_class)
                circuit.record_failure()
                last_outcome = outcome
                last_error_class = err_class
                if not is_fallback_eligible(outcome, error_class=err_class):
                    break
                fallback_used = is_fallback
                continue

            outcome = status_to_outcome(domain_result.status)
            self._append_lineage(
                provider_name,
                outcome,
                domain_result.safe_error_code,
                latency_ms=domain_result.latency_ms,
            )
            if domain_result.status != ResearchFetchStatus.SUCCEEDED:
                await self._record_attempt(
                    url=url,
                    normalized_url=normalized,
                    query_id=query_id,
                    provider=provider_name,
                    attempt_number=attempt_num,
                    outcome=outcome,
                    http_status=domain_result.http_status,
                    content_type=domain_result.content_type,
                    content_length=domain_result.byte_count,
                    extracted_len=0,
                    retryable=is_fallback_eligible(
                        outcome,
                        error_class=domain_result.safe_error_code,
                    ),
                    fallback_used=is_fallback,
                    error_class=domain_result.safe_error_code,
                    safe_msg=safe_error_message(outcome),
                    started=started,
                )
                circuit.record_failure()
                last_outcome = outcome
                last_error_class = domain_result.safe_error_code
                if self._metrics:
                    self._metrics.record_fetch_fallback(
                        provider_name,
                        domain_result.safe_error_code or outcome.value,
                    )
                if not is_fallback_eligible(outcome, error_class=domain_result.safe_error_code):
                    break
                fallback_used = is_fallback
                continue

            body_outcome, text, extraction = self._apply_content_extraction(
                raw=domain_result.extracted_text,
                url=normalized,
                content_type=domain_result.content_type or "text/plain",
                title_hint=domain_result.title,
            )
            self._last_extraction = extraction
            finished = utc_now()
            latency = int((finished - started).total_seconds() * 1000)
            await self._ledger.append(
                BivFetchLedgerTable(
                    run_id=self._run_id,
                    correlation_id=self._correlation_id,
                    query_id=query_id,
                    source_url=url[:2048],
                    normalized_url=normalized[:2048],
                    provider=provider_name,
                    attempt_number=attempt_num,
                    started_at=started,
                    finished_at=finished,
                    latency_ms=latency,
                    http_status=domain_result.http_status,
                    outcome_code=body_outcome.value,
                    content_type=domain_result.content_type,
                    content_length=domain_result.byte_count or None,
                    retryable=is_fallback_eligible(body_outcome),
                    fallback_used=is_fallback,
                    error_class=(
                        None
                        if body_outcome == BivFetchOutcomeCode.SUCCESS
                        else "ExtractReject"
                    ),
                    safe_error_message=safe_error_message(body_outcome),
                    raw_content_stored=False,
                    extracted_text_length=len(text.strip()),
                )
            )
            self._total_attempts += 1
            if self._metrics:
                self._metrics.record_fetch_attempt(
                    body_outcome,
                    fallback=is_fallback,
                    normalized_url=normalized,
                    provider=provider_name,
                )

            if body_outcome != BivFetchOutcomeCode.SUCCESS:
                circuit.record_failure()
                last_outcome = body_outcome
                last_error_class = "ExtractReject"
                if not is_fallback_eligible(body_outcome):
                    break
                fallback_used = is_fallback
                continue

            circuit.record_success()
            fetch_result = SourceFetchResult(
                url=normalized,
                provider=provider_name,
                candidate=SourceCandidate(
                    url=normalized,
                    title=domain_result.title or "",
                    provider=provider_name,
                ),
                normalized_text_excerpt=text,
            )
            final = self._success_result(
                url=url,
                normalized=normalized,
                outcome=body_outcome,
                fetch_result=fetch_result,
                audit_id=None,
                text=text,
                title=domain_result.title,
                fallback_used=is_fallback,
                provider=provider_name,
            )
            self._cache_success(normalized, final)
            return final

        if self._metrics:
            self._metrics.record_all_providers_failed()
        return FetchOrchestratorResult(
            success=False,
            url=url,
            normalized_url=normalized,
            outcome=last_outcome,
            fetch_result=None,
            audit_id=None,
            extracted_text="",
            title=None,
            fallback_used=fallback_used,
            attempt_lineage=list(self._lineage),
            provider=None,
        )

    def _success_result(
        self,
        *,
        url: str,
        normalized: str,
        outcome: BivFetchOutcomeCode,
        fetch_result: SourceFetchResult | None,
        audit_id: UUID | None,
        text: str,
        title: str | None,
        fallback_used: bool,
        provider: str,
    ) -> FetchOrchestratorResult:
        return FetchOrchestratorResult(
            success=True,
            url=url,
            normalized_url=normalized,
            outcome=outcome,
            fetch_result=fetch_result,
            audit_id=audit_id,
            extracted_text=text,
            title=title,
            fallback_used=fallback_used,
            extraction=getattr(self, "_last_extraction", None),
            provider=provider,
            attempt_lineage=list(self._lineage),
        )

    def _cache_success(self, normalized: str, result: FetchOrchestratorResult) -> None:
        if self._settings.research_fetch_cache_enabled and result.success:
            self._success_cache[normalized] = result

    def _append_lineage(
        self,
        provider: str,
        outcome: BivFetchOutcomeCode,
        safe_error_code: str | None,
        *,
        latency_ms: int | None = None,
    ) -> None:
        if outcome == BivFetchOutcomeCode.SUCCESS:
            status = ResearchFetchStatus.SUCCEEDED
        else:
            status = ResearchFetchStatus.UNKNOWN_FAILURE
        if outcome == BivFetchOutcomeCode.CREDITS_EXHAUSTED:
            status = ResearchFetchStatus.CREDITS_EXHAUSTED
        elif outcome == BivFetchOutcomeCode.RATE_LIMITED:
            status = ResearchFetchStatus.RATE_LIMITED
        elif outcome == BivFetchOutcomeCode.TIMEOUT:
            status = ResearchFetchStatus.TIMEOUT
        elif outcome == BivFetchOutcomeCode.UNSAFE_URL:
            status = ResearchFetchStatus.UNSAFE_URL
        self._lineage.append(
            FetchAttemptLineage(
                provider=provider,
                status=status,
                safe_error_code=safe_error_code,
                latency_ms=latency_ms,
            )
        )

    async def _fetch_firecrawl(
        self,
        url: str,
        *,
        mcp_fetch,
        started,
        query_id: str = "",
        url_original: str | None = None,
        is_fallback: bool = False,
    ) -> tuple[
        BivFetchOutcomeCode,
        SourceFetchResult | None,
        UUID | None,
        str,
        str | None,
        int | None,
        str | None,
    ]:
        source_url = url_original or url
        attempt_num = self._attempts_for_url.get(url, 0) + 1
        timeout = self._settings.research_fetch_timeout_seconds
        try:
            if mcp_fetch is not None:
                fetch_result, audit_id = await asyncio.wait_for(
                    mcp_fetch(url=url),
                    timeout=timeout,
                )
            else:
                fetch_result = await asyncio.wait_for(
                    self._firecrawl.fetch(url),
                    timeout=timeout,
                )
                audit_id = None
        except TimeoutError:
            outcome = BivFetchOutcomeCode.TIMEOUT
            await self._record_attempt(
                url=source_url,
                normalized_url=url,
                query_id=query_id,
                provider=self.PROVIDER_FIRECRAWL,
                attempt_number=attempt_num,
                outcome=outcome,
                http_status=None,
                content_type="text/markdown",
                content_length=0,
                extracted_len=0,
                retryable=True,
                fallback_used=is_fallback,
                error_class="TimeoutError",
                safe_msg=safe_error_message(outcome),
                started=started,
            )
            return outcome, None, None, "", None, None, None
        except BusinessToolError as exc:
            outcome = map_business_tool_error(exc.category)
            await self._record_attempt(
                url=source_url,
                normalized_url=url,
                query_id=query_id,
                provider=self.PROVIDER_FIRECRAWL,
                attempt_number=attempt_num,
                outcome=outcome,
                http_status=None,
                content_type=None,
                content_length=0,
                extracted_len=0,
                retryable=is_fallback_eligible(outcome, error_class=exc.category),
                fallback_used=is_fallback,
                error_class=exc.category,
                safe_msg=(exc.user_message or str(exc))[:500],
                started=started,
            )
            if self._metrics and exc.category == "credits_exhausted":
                self._metrics.record_credits_exhausted(self.PROVIDER_FIRECRAWL)
            return outcome, None, None, "", None, None, None

        text = fetch_result.normalized_text_excerpt or ""
        title = fetch_result.candidate.title if fetch_result.candidate else None
        body_outcome, text, extraction = self._apply_content_extraction(
            raw=text,
            url=url,
            content_type="text/markdown",
            title_hint=title,
        )
        self._last_extraction = extraction
        finished = utc_now()
        latency = int((finished - started).total_seconds() * 1000)
        await self._ledger.append(
            BivFetchLedgerTable(
                run_id=self._run_id,
                correlation_id=self._correlation_id,
                query_id=query_id,
                source_url=source_url[:2048],
                normalized_url=url[:2048],
                provider=self.PROVIDER_FIRECRAWL,
                attempt_number=attempt_num,
                started_at=started,
                finished_at=finished,
                latency_ms=latency,
                http_status=200 if body_outcome == BivFetchOutcomeCode.SUCCESS else None,
                outcome_code=body_outcome.value,
                content_type="text/markdown",
                content_length=len(text.encode("utf-8", errors="ignore")),
                retryable=is_fallback_eligible(body_outcome),
                fallback_used=is_fallback,
                error_class=(
                    None if body_outcome == BivFetchOutcomeCode.SUCCESS else "ExtractReject"
                ),
                safe_error_message=safe_error_message(body_outcome),
                raw_content_stored=False,
                extracted_text_length=len(text.strip()),
            )
        )
        self._total_attempts += 1
        if self._metrics:
            self._metrics.record_fetch_attempt(
                body_outcome,
                fallback=is_fallback,
                normalized_url=url,
                provider=self.PROVIDER_FIRECRAWL,
            )
        if body_outcome != BivFetchOutcomeCode.SUCCESS:
            return body_outcome, None, audit_id, text, title, 200, "text/markdown"
        return body_outcome, fetch_result, audit_id, text, title, 200, "text/markdown"

    def _apply_content_extraction(
        self,
        *,
        raw: str,
        url: str,
        content_type: str,
        title_hint: str | None,
    ) -> tuple[BivFetchOutcomeCode, str, ContentExtractionResult]:
        extraction = extract_and_normalize_document(
            raw,
            source_url=url,
            header_content_type=content_type,
            title_hint=title_hint,
            run_context=self._extraction_ctx,
        )
        self._normalized_documents.append(extraction)
        if self._metrics:
            accepted = extraction.extraction_status == ExtractionStatus.ACCEPTED
            self._metrics.record_extraction(
                success=accepted,
                boilerplate_rejected=not accepted
                and extraction.rejection_reason is not None
                and "boilerplate" in extraction.rejection_reason.value,
            )
            if accepted:
                self._metrics.record_normalized_document(
                    duplicate=False,
                    metadata_complete=extraction.metadata_complete,
                )
            elif extraction.rejection_reason and "duplicate" in extraction.rejection_reason.value:
                self._metrics.record_normalized_document(duplicate=True)
        if extraction.extraction_status == ExtractionStatus.ACCEPTED:
            return BivFetchOutcomeCode.SUCCESS, extraction.clean_text, extraction
        reason = extraction.rejection_reason
        assert reason is not None
        outcome = rejection_to_fetch_outcome(reason)
        return outcome, extraction.clean_text, extraction

    async def _record_attempt(
        self,
        *,
        url: str,
        normalized_url: str,
        query_id: str,
        provider: str,
        attempt_number: int,
        outcome: BivFetchOutcomeCode,
        http_status: int | None,
        content_type: str | None,
        content_length: int,
        extracted_len: int,
        retryable: bool,
        fallback_used: bool,
        error_class: str | None,
        safe_msg: str | None,
        started,
    ) -> None:
        finished = utc_now()
        latency = int((finished - started).total_seconds() * 1000)
        await self._ledger.append(
            BivFetchLedgerTable(
                run_id=self._run_id,
                correlation_id=self._correlation_id,
                query_id=query_id,
                source_url=url[:2048],
                normalized_url=normalized_url[:2048],
                provider=provider,
                attempt_number=attempt_number,
                started_at=started,
                finished_at=finished,
                latency_ms=latency,
                http_status=http_status,
                outcome_code=outcome.value,
                content_type=content_type,
                content_length=content_length or None,
                retryable=retryable,
                fallback_used=fallback_used,
                error_class=error_class,
                safe_error_message=safe_msg,
                raw_content_stored=False,
                extracted_text_length=extracted_len,
            )
        )
        self._total_attempts += 1
        if self._metrics:
            self._metrics.record_fetch_attempt(
                outcome,
                fallback=fallback_used,
                normalized_url=normalized_url,
                provider=provider,
            )

    def _next_attempt(self, normalized_url: str) -> int:
        count = self._attempts_for_url.get(normalized_url, 0) + 1
        self._attempts_for_url[normalized_url] = count
        return count

    @staticmethod
    def _backoff_delay(*, attempt: int) -> float:
        base = min(2.0**attempt, 8.0)
        return base + random.uniform(0, 0.5)

    def circuit_snapshot(self) -> dict[str, str]:
        return self._circuits.snapshot()
