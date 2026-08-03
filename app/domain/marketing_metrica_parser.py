"""Rule-based Metrica natural language → API payload parser (Phase AI.219)."""

from __future__ import annotations

from app.marketing.data_tools.metrica_dimensions import (
    default_metrics,
    resolve_dimension,
    resolve_metric,
)
from app.schemas.contracts import MetricaToolInput


def parse_metrica_input(payload: MetricaToolInput) -> MetricaToolInput:
    """Enrich structured Metrica input from aliases and optional natural language."""
    metrics = list(payload.metrics)
    dimensions = list(payload.dimensions)

    if payload.natural_language:
        text = payload.natural_language.lower()
        for token in ("visits", "users", "pageviews", "traffic", "device", "content"):
            if token in text:
                metric = resolve_metric(token)
                dimension = resolve_dimension(token)
                if metric and metric not in metrics:
                    metrics.append(metric)
                if dimension and dimension not in dimensions:
                    dimensions.append(dimension)

    normalized_metrics = []
    for item in metrics:
        resolved = resolve_metric(item) or item.strip()
        if resolved and resolved not in normalized_metrics:
            normalized_metrics.append(resolved)

    normalized_dimensions = []
    for item in dimensions:
        resolved = resolve_dimension(item) or item.strip()
        if resolved and resolved not in normalized_dimensions:
            normalized_dimensions.append(resolved)

    if not normalized_metrics:
        normalized_metrics = default_metrics()

    return payload.model_copy(
        update={
            "metrics": normalized_metrics,
            "dimensions": normalized_dimensions,
        },
    )
