# Reference Set policy (H2.6A-R)

- Max **15** stored assets per set.
- Provider request uses ranked subset (`REFERENCE_PROVIDER_MAX_IMAGES`, default 10).
- Selection is recorded: `selected_reference_ids`, `excluded_reference_ids`, reasons.
- No silent omission — UI may show “Использовано N из M референсов…”.
- Status: draft → ready → used → archived.
- Cross-owner access denied.
