"""Higgsfield MCP connector — adapter candidate (CONN-HF-01.1)."""

from app.connectors.higgsfield.adapter import HiggsfieldConnectorAdapter
from app.connectors.higgsfield.constants import (
    HIGGSFIELD_CONNECTOR_ID,
    HIGGSFIELD_CONNECTOR_VERIFICATION_STATUS,
    HIGGSFIELD_CONNECTOR_VERSION,
    HIGGSFIELD_OFFICIAL_MCP_ENDPOINT,
    MEDIA_OP_ASSET_FETCH,
    MEDIA_OP_IMAGE_GENERATE,
    MEDIA_OP_JOB_GET_STATUS,
    MEDIA_OP_VIDEO_GENERATE,
)
from app.connectors.higgsfield.descriptor import (
    all_higgsfield_tools,
    higgsfield_descriptor,
)
from app.connectors.higgsfield.registry import build_higgsfield_gateway

__all__ = [
    "HIGGSFIELD_CONNECTOR_ID",
    "HIGGSFIELD_CONNECTOR_VERIFICATION_STATUS",
    "HIGGSFIELD_CONNECTOR_VERSION",
    "HIGGSFIELD_OFFICIAL_MCP_ENDPOINT",
    "MEDIA_OP_ASSET_FETCH",
    "MEDIA_OP_IMAGE_GENERATE",
    "MEDIA_OP_JOB_GET_STATUS",
    "MEDIA_OP_VIDEO_GENERATE",
    "HiggsfieldConnectorAdapter",
    "all_higgsfield_tools",
    "build_higgsfield_gateway",
    "higgsfield_descriptor",
]
