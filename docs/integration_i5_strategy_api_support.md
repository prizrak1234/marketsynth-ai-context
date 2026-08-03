# Integration I5 — Strategy API support

| Endpoint | Used in I5 | Side effects |
|----------|------------|--------------|
| `GET /projects/{id}/marketing-plans` | yes | none |
| `GET .../marketing-plans/{id}` | available | none |
| `GET .../versions` | characterized | none |
| `POST .../approve` | **not** from Strategy UI | pins approved version |
| `POST .../archive` | not from Strategy UI | archives |
| `POST .../execution-runs` | **not** | would start execution spine |
| `POST .../marketing-scenarios/{id}/create-plan` | **not** | creates draft plan |

No new Strategy endpoints in I5. No duplicate planner APIs.
