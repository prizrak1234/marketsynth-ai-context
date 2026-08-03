"""Pipeline stage metrics recorder for BIV research runs."""

from __future__ import annotations

from app.business_idea_validation.fetch_circuit_breaker import get_fetch_circuit_registry
from app.schemas.contracts import (
    BivFetchOutcomeCode,
    BivPipelineMetrics,
    BivRunObservability,
)


class BivPipelineMetricsRecorder:
    def __init__(self) -> None:
        self._data = BivPipelineMetrics()
        self._attempted_urls: set[str] = set()
        self._successful_urls: set[str] = set()

    @property
    def data(self) -> BivPipelineMetrics:
        self._refresh_fetch_rate()
        self._data.fetch.provider_circuit_state = get_fetch_circuit_registry().snapshot()
        return self._data

    def record_queries_generated(self, count: int) -> None:
        self._data.discovery.queries_generated = count

    def record_search_executed(self, *, success: bool, candidates: int) -> None:
        self._data.discovery.queries_executed += 1
        self._data.discovery.search_requests += 1
        if success:
            self._data.discovery.search_success_count += 1
        self._data.discovery.discovered_urls += candidates

    def register_unique_url(self, *, duplicate: bool = False, ineligible: bool = False) -> None:
        if ineligible:
            self._data.discovery.ineligible_urls += 1
        elif duplicate:
            self._data.discovery.duplicate_urls += 1
        else:
            self._data.discovery.unique_urls += 1

    def record_fetch_eligible(self) -> None:
        self._data.fetch.eligible_urls += 1

    def record_fetch_attempt(
        self,
        outcome: BivFetchOutcomeCode,
        *,
        fallback: bool = False,
        normalized_url: str | None = None,
        provider: str | None = None,
    ) -> None:
        self._data.fetch.fetch_attempts += 1
        if provider:
            self._data.fetch.fetch_attempts_by_provider[provider] = (
                self._data.fetch.fetch_attempts_by_provider.get(provider, 0) + 1
            )
        if normalized_url:
            self._attempted_urls.add(normalized_url)
            if outcome == BivFetchOutcomeCode.SUCCESS:
                self._successful_urls.add(normalized_url)
        key = outcome.value
        if outcome == BivFetchOutcomeCode.SUCCESS:
            self._data.fetch.fetch_success_count += 1
            if provider:
                self._data.fetch.fetch_success_by_provider[provider] = (
                    self._data.fetch.fetch_success_by_provider.get(provider, 0) + 1
                )
            if fallback:
                self._data.fetch.fallback_success_count += 1
        elif outcome == BivFetchOutcomeCode.DUPLICATE_URL:
            self._data.fetch.duplicate_url_skipped_total += 1
            self._data.fetch.cache_hit_total += 1
        else:
            self._data.fetch.fetch_failure_count += 1
            self._data.fetch.failures_by_outcome[key] = (
                self._data.fetch.failures_by_outcome.get(key, 0) + 1
            )

    def record_fetch_fallback(self, provider: str, reason: str) -> None:
        bucket = f"{provider}:{reason}"
        self._data.fetch.fetch_fallback_total[bucket] = (
            self._data.fetch.fetch_fallback_total.get(bucket, 0) + 1
        )

    def record_credits_exhausted(self, provider: str) -> None:
        self._data.fetch.provider_credits_exhausted_total[provider] = (
            self._data.fetch.provider_credits_exhausted_total.get(provider, 0) + 1
        )

    def record_all_providers_failed(self) -> None:
        self._data.fetch.all_providers_failed_total += 1

    def record_extraction(self, *, success: bool, boilerplate_rejected: bool = False) -> None:
        self._data.extract.extraction_attempts += 1
        if success:
            self._data.extract.extraction_success_count += 1
        elif boilerplate_rejected:
            self._data.extract.rejected_boilerplate += 1
        else:
            self._data.extract.empty_extractions += 1
        self._refresh_extraction_rate()

    def record_normalized_document(self, *, duplicate: bool = False, metadata_complete: bool = False) -> None:
        if duplicate:
            self._data.normalize.duplicate_documents += 1
        else:
            self._data.normalize.normalized_documents += 1
        total = self._data.normalize.normalized_documents + self._data.normalize.duplicate_documents
        if total:
            complete = self._data.normalize.normalized_documents
            if metadata_complete:
                complete += 0
            self._data.normalize.metadata_complete_rate = min(1.0, complete / total)

    def record_evidence(self, *, category: str, accepted: bool, rejection_reason: str | None = None) -> None:
        self._data.evidence.evidence_candidates += 1
        if accepted:
            self._data.evidence.accepted_evidence += 1
            self._data.evidence.evidence_by_category[category] = (
                self._data.evidence.evidence_by_category.get(category, 0) + 1
            )
        else:
            self._data.evidence.rejected_evidence += 1
            if rejection_reason:
                self._data.evidence.rejection_reasons[rejection_reason] = (
                    self._data.evidence.rejection_reasons.get(rejection_reason, 0) + 1
                )

    def set_evidence_coverage(self, rate: float) -> None:
        self._data.evidence.evidence_coverage = max(0.0, min(1.0, rate))

    def record_finding(self, *, with_evidence: bool) -> None:
        self._data.reasoning.findings_count += 1
        if with_evidence:
            self._data.reasoning.findings_with_evidence += 1
        else:
            self._data.reasoning.unsupported_findings += 1

    def set_citation_coverage(self, rate: float) -> None:
        self._data.reasoning.citation_coverage = max(0.0, min(1.0, rate))

    def set_contradiction_count(self, count: int) -> None:
        self._data.reasoning.contradiction_count = count

    def set_report_validation(
        self,
        *,
        generated: bool,
        passed: bool,
        empty_links: int = 0,
        raw_dom: int = 0,
        unsupported: int = 0,
        export_passed: bool = False,
    ) -> None:
        self._data.report.report_generated = generated
        self._data.report.report_validation_passed = passed
        self._data.report.empty_links = empty_links
        self._data.report.raw_dom_detected = raw_dom
        self._data.report.unsupported_claims = unsupported
        self._data.report.export_validation_passed = export_passed

    def _refresh_fetch_rate(self) -> None:
        attempted_eligible = len(self._attempted_urls)
        self._data.fetch.attempted_eligible_urls = attempted_eligible
        if attempted_eligible > 0:
            self._data.fetch.fetch_success_rate = len(self._successful_urls) / attempted_eligible
        elif self._data.fetch.eligible_urls > 0:
            self._data.fetch.fetch_success_rate = 0.0

    def _refresh_extraction_rate(self) -> None:
        if self._data.extract.extraction_attempts > 0:
            self._data.extract.extraction_success_rate = (
                self._data.extract.extraction_success_count / self._data.extract.extraction_attempts
            )

    def attach_to_observability(self, obs: BivRunObservability) -> None:
        obs.pipeline_metrics = self.data
