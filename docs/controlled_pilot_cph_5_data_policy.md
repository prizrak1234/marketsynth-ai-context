# CPH.5 — Pilot data policy (minimum)

- Separate test fixtures from any real business pilot data when possible
- No production credentials in pilot
- Treat Brief/Evidence as sensitive — redact from logs
- Backups outside git; limited operator access
- Retention per CPH.4 RPO/RTO doc
- Account removal: manual DB disable + session revoke (no self-serve deletion portal yet)
- Incident notification: local operator / owner responsibility

This document does **not** claim GDPR/SOC2 or other compliance certifications.
