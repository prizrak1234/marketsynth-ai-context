"""Safe, secret-free status for video aggregator / MCP recovery audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.media_generation.gptunnel_video_gateway import try_build_gptunnel_video_gateway
from app.media_generation.video_readiness import (
    image_to_video_live_verified,
    paid_smoke_status,
    smoke_public_summary,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DISCOVERY_PATH = REPO_ROOT / "data/audits/video_aggregator_discovery.json"
MCP_AUDIT_PATH = REPO_ROOT / "data/audits/mcp_pencil_openknowledge_audit.json"


def _secret_present(secret: Any) -> bool:
    if secret is None:
        return False
    try:
        return bool(secret.get_secret_value().strip())
    except Exception:
        return bool(str(secret).strip())


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def video_aggregator_public_status(settings: Settings) -> dict[str, Any]:
    """Owner/settings-safe view — no keys, no raw paths secrets."""
    discovery = _load_json(DISCOVERY_PATH)
    disc = discovery.get("discovery") if isinstance(discovery.get("discovery"), dict) else {}
    pilot = (
        discovery.get("pilot_recommendation")
        if isinstance(discovery.get("pilot_recommendation"), dict)
        else {}
    )
    model = pilot.get("selected_model")
    cost = pilot.get("estimated_max_cost_units")
    models_ok = disc.get("http_status") == 200 and not disc.get("error")
    auth = _secret_present(settings.gptunnel_api_key)
    i2v_doc = bool((pilot.get("p0_checklist") or {}).get("image_to_video_documented"))
    video_client = try_build_gptunnel_video_gateway(settings)
    live_verified = image_to_video_live_verified(settings)
    limitations = [
        "Marketsynth wires GPTunnel for images (GptunnelImagesProvider).",
        "Video Router registers GPTunnel CreativeLab when VIDEO_GENERATION_ENABLED=true.",
        "CreativeLab media/create i2v accepts images[] as fetchable URLs; no REST multipart upload.",
    ]
    if video_client is None:
        limitations.append("Video adapter not connected — enable VIDEO_GENERATION_ENABLED + GPTUNNEL_API_KEY.")
    if not live_verified:
        limitations.append(
            "Paid i2v smoke not verified — POST /media-generation/video-smoke/execute "
            "with explicit_confirmation=true after owner review."
        )
    from app.media_generation.signed_asset_urls import signed_url_readiness

    signed = signed_url_readiness(settings)
    return {
        "code": "gptunnel_creativelab",
        "configured": auth,
        "base_url_safe": (settings.gptunnel_base_url or "https://gptunnel.ru/v1").rstrip("/"),
        "auth_present": auth,
        "api_style": "async_media_create_result",
        "model_discovery_available": True,
        "model_discovery_live_ok": models_ok,
        "live_model_count": disc.get("model_count"),
        "selected_pilot_model": model or settings.gptunnel_video_model,
        "image_to_video_documented": i2v_doc,
        "image_to_video_live_verified": live_verified,
        "estimated_pilot_cost_units": cost,
        "cost_status": "known_from_catalog" if cost is not None else "unknown",
        "health": "configured" if auth and models_ok else ("auth_missing" if not auth else "discovery_failed"),
        "paid_smoke_status": paid_smoke_status(),
        "live_smoke_summary": smoke_public_summary(),
        "video_client_connected": video_client is not None,
        "input_image_transport": {
            "creativelab_multipart_upload": False,
            "creativelab_base64_faq": False,
            "creativelab_images_url_array": True,
            "mcp_upload_media_separate_surface": True,
            "marketsynth_signed_url": signed,
        },
        "limitations": limitations,
    }


def mcp_tools_public_status() -> dict[str, Any]:
    audit = _load_json(MCP_AUDIT_PATH)
    pencil = audit.get("pencil") if isinstance(audit.get("pencil"), dict) else {}
    ok = audit.get("openknowledge") if isinstance(audit.get("openknowledge"), dict) else {}
    return {
        "pencil": {
            "connected": pencil.get("cursor_registered") is True,
            "host_registrations": pencil.get("host_registrations") or [],
            "scope": "Design Operator (recommended)",
            "role": pencil.get("role_decision") or "developer_only_pending_operator_wiring",
            "allowed_workspace": pencil.get("allowed_workspace") or "approved design workspace only",
            "smoke_status": pencil.get("smoke_status") or "not_run",
            "limitation": pencil.get("limitation")
            or "Cursor MCP not registered; Claude/VS Code host-level only.",
        },
        "openknowledge": {
            "connected": ok.get("found") is True,
            "scope": "Knowledge Authoring",
            "role": ok.get("role_decision") or "not_present",
            "governed_publication_required": True,
            "smoke_status": ok.get("smoke_status") or "not_applicable_missing",
            "limitation": ok.get("limitation")
            or "No OpenKnowledge MCP registration or .ok root found.",
        },
        "admission_policy": "deny_by_default",
        "note": "Host MCP ≠ Marketsynth product-runtime integration.",
    }


def _design_operator_port_status() -> dict[str, object]:
    return {
        "port": "DesignOperatorPort",
        "role": "B_internal_operator_design_tool",
        "ports_registered": True,
        "clients_connected": False,
        "allowed_ops": [
            "get_editor_state",
            "batch_get",
            "batch_design",
            "get_screenshot",
        ],
        "note": "Pencil MCP deferred until editorial conveyor freeze",
    }


def _knowledge_authoring_port_status() -> dict[str, object]:
    return {
        "port": "KnowledgeAuthoringPort",
        "ports_registered": True,
        "clients_connected": False,
        "runtime_sot": "postgresql_knowledge_governance",
        "bridge": "openknowledge_doc -> knowledge_candidate -> human_review -> kg_publication",
        "note": "Do not invent OpenKnowledge as Runtime SoT",
    }


def content_factory_integrations_status(settings: Settings) -> dict[str, Any]:
    from app.media_generation.gateway import gateway_port_status

    return {
        "video_aggregator": video_aggregator_public_status(settings),
        "mcp": mcp_tools_public_status(),
        "video_skill_status": "ready_after_live_smoke" if image_to_video_live_verified() else "not_created_pending_smoke",
        "checkpoint": "VS1_FOUNDATION" if try_build_gptunnel_video_gateway(settings) else "READY_FOR_OWNER_REVIEW_AUDIT_ONLY",
        "commercial_pipeline": {
            "editorial_core": "active",
            "paid_calls": image_to_video_live_verified(),
            "ports": {
                "image_video_gateway": gateway_port_status(settings),
                "design_operator": _design_operator_port_status(),
                "knowledge_authoring": _knowledge_authoring_port_status(),
            },
        },
    }
