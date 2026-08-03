# Deferred Patterns — KB-WPL-01.3B

Patterns intentionally **not** included in the 01.3B core library.

## Explicitly deferred categories

### Spend / billing (owner directive)

- billing_reconciliation
- ad_spend_tracking
- payment_capture
- invoice_generation

### Destructive / high-risk

- bulk_delete_without_review
- credential_rotation_without_approval
- production_config_overwrite

### Not yet source-backed (priority list remainder)

| Candidate | Reason deferred |
|-----------|-----------------|
| manual_review_queue | Overlaps pilot draft_to_human_approval; wait for distinct sources |
| change_review_before_activation | Needs dedicated activation-review sources |
| timeout_and_resume | Overlaps checkpoint_and_resume family |
| partial_failure_isolation | Needs isolated failure topology evidence |
| scheduled_recovery | Needs cron/recovery crosswalk |
| incremental_processing | Overlaps pagination family |
| structured_output_validation | Covered by quality_gate + pilot structured_LLM |
| deduplication_before_write | Needs write-path dedup sources |
| prompt_injection_filter | Needs dedicated untrusted-input workflows |
| reflection_and_revision | Needs multi-pass revision sources |
| campaign_result_to_learning_candidate | Second learning pattern — defer to 01.3C |
| long_form_to_social_repurposing | Marketing slice — defer |
| approved_content_to_publication | Overlaps publication_confirmation |
| review_analysis_to_insight | Needs analytics insight sources |
| workflow_documentation | Engineering meta — defer to 01.4 |
| credential_preserving_update | Engineering — defer |
| provider_version_compatibility | Engineering — defer |
| sandbox_last_mile_debug | Engineering — defer |
| test_fixture_replay | Engineering — defer |

## Maturity ceiling

No deferred pattern may be promoted to `platform_adapted` without runtime benchmark —
tests verify contract invariants only, not real execution.

## Next expansion (01.3C candidate)

After owner accepts 01.3B, evaluate deferred list against remaining ~22 catalog candidates
with same lineage gates. Target: freeze at 20–25 total, not catalog-wide coverage.
