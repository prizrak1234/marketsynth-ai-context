# Knowledge Linking Methodology

Adapted methodology for deterministic knowledge link analysis within Marketsynth
Knowledge Core contracts.

## Principles

1. **Links are proposed, not applied** — output is a reviewable report only.
2. **Explicit evidence required** — high-confidence links need deterministic basis.
3. **Visibility before analysis** — tenant filtering precedes orphan/duplicate detection.
4. **Historical versions preserved** — supersession does not delete lineage.
5. **Contradictions surfaced, not resolved** — human reviewer owns resolution.

## Link validation

- Resolve source and target artifact IDs against scoped index.
- Reject unknown targets as generic not-found (no cross-tenant leakage).
- Validate relation type against finite taxonomy.
- Require reason and supporting evidence for every proposed link.

## Orphan detection

- Calculate after visibility filtering.
- Exempt standalone source archives, frozen root indexes, intentionally isolated rejects.
- Hidden tenant-private artifacts excluded from orphan counts.

## Broken-link reports

- Classify failure type: missing target, hash mismatch, stale reference, etc.
- Mark authoritative schema/hash mismatches as blocking.
- Include remediation guidance without auto-fix.

## Index recommendations

- Identify missing domain indexes, stale entries, orphan collections.
- Propose index entries — never write index files automatically.

## Related-document logic

- Prefer explicit declared references over title similarity.
- Declared dependencies yield high-confidence `depends_on` links.
- Similarity alone caps confidence at medium or lower.
