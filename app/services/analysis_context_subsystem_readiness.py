"""PRODUCT-01.3A analysis-context subsystem readiness (no auto-migrate)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine

ANALYSIS_CONTEXT_TABLE = "analysis_contexts"
BIV_TABLE = "business_idea_validation_runs"
BIV_CONTEXT_COLUMN = "analysis_context_id"
BIV_HASH_COLUMN = "input_snapshot_hash"
OPENAPI_PATH_PREFIX = "/projects/{project_id}/analysis-contexts"


@dataclass(frozen=True)
class AnalysisContextSubsystemStatus:
    ready: bool
    table_present: bool
    biv_bridge_columns_present: bool
    openapi_paths_present: bool
    detail: str

    def as_dict(self) -> dict[str, object]:
        return {
            "ready": self.ready,
            "table_present": self.table_present,
            "biv_bridge_columns_present": self.biv_bridge_columns_present,
            "openapi_paths_present": self.openapi_paths_present,
            "detail": self.detail,
        }


def _openapi_has_analysis_context_paths(openapi_schema: dict) -> bool:
    paths = openapi_schema.get("paths", {})
    required = {
        "/projects/{project_id}/analysis-contexts",
        "/projects/{project_id}/analysis-contexts/current",
        "/projects/{project_id}/analysis-contexts/{context_id}/confirm",
    }
    return required.issubset(paths.keys())


async def inspect_analysis_context_subsystem(engine: AsyncEngine) -> AnalysisContextSubsystemStatus:
    table_present = False
    biv_bridge_columns_present = False

    async with engine.connect() as conn:
        def _inspect(sync_conn):  # noqa: ANN001
            inspector = inspect(sync_conn)
            tables = set(inspector.get_table_names())
            table_ok = ANALYSIS_CONTEXT_TABLE in tables
            biv_ok = False
            if BIV_TABLE in tables:
                cols = {c["name"] for c in inspector.get_columns(BIV_TABLE)}
                biv_ok = BIV_CONTEXT_COLUMN in cols and BIV_HASH_COLUMN in cols
            return table_ok, biv_ok

        table_present, biv_bridge_columns_present = await conn.run_sync(_inspect)

    ready = table_present and biv_bridge_columns_present
    if not table_present:
        detail = "analysis_contexts_table_missing_run_repair_script"
    elif not biv_bridge_columns_present:
        detail = "business_idea_validation_runs_missing_analysis_context_columns"
    else:
        detail = "ok"
    return AnalysisContextSubsystemStatus(
        ready=ready,
        table_present=table_present,
        biv_bridge_columns_present=biv_bridge_columns_present,
        openapi_paths_present=False,
        detail=detail,
    )


async def check_analysis_context_subsystem(
    engine: AsyncEngine,
    *,
    openapi_schema: dict | None = None,
) -> AnalysisContextSubsystemStatus:
    status = await inspect_analysis_context_subsystem(engine)
    openapi_ok = bool(openapi_schema and _openapi_has_analysis_context_paths(openapi_schema))
    ready = status.ready and (openapi_schema is None or openapi_ok)
    detail = status.detail
    if status.ready and openapi_schema is not None and not openapi_ok:
        detail = "analysis_context_openapi_paths_missing"
    return AnalysisContextSubsystemStatus(
        ready=ready,
        table_present=status.table_present,
        biv_bridge_columns_present=status.biv_bridge_columns_present,
        openapi_paths_present=openapi_ok,
        detail=detail,
    )


async def probe_table_exists(engine: AsyncEngine, table_name: str) -> bool:
    async with engine.connect() as conn:
        try:
            await conn.execute(text(f"SELECT 1 FROM {table_name} LIMIT 0"))
            return True
        except Exception:  # noqa: BLE001
            return False
