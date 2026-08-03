# Database migrations

Alembic scripts live in project root: `alembic/versions/`.

```bash
docker compose up -d
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "describe_change"
```
