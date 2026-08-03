# Source Risk Register

## Critical risks

1. **185** workflows contain code nodes
2. **223** workflows reference credentials
3. **119** workflows have publication nodes
4. **1** workflows have destructive markers
5. **26** workflows use community/unknown nodes
6. All archives: **license_status = unknown**
7. **20** exports have active=true (informational only)

## Mitigations

- Static parse only — no n8n import
- Metadata catalog — no workflow bodies in production packages
- Pattern extraction requires ≥2 sources or manual audit (KB-WPL-01.3)
- Publication/spend/destructive patterns require human approval gates
