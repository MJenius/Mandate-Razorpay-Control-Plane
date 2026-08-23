"""Prometheus metrics scrape endpoint for Mandate Control Plane."""

from fastapi import APIRouter, Response

from packages.shared.observability import get_prometheus_metrics_bytes

router = APIRouter(tags=["Observability"])


@router.get("/metrics")
async def metrics_endpoint() -> Response:
    """Standard Prometheus scraping endpoint returning real-time control plane telemetry."""
    metrics_data, content_type = get_prometheus_metrics_bytes()
    return Response(content=metrics_data, media_type=content_type)
