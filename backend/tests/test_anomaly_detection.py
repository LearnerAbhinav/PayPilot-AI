from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_detect_anomalies_returns_list(test_client: AsyncClient):
    mock_anomalies = [
        {
            "type": "revenue_drop",
            "severity": "medium",
            "metric": "daily_revenue",
            "current_value": 5000.0,
            "baseline": 15000.0,
            "percentage_change": -66.67,
            "explanation": "Revenue dropped on 2026-08-15",
        },
        {
            "type": "failure_rate_spike",
            "severity": "high",
            "metric": "failure_rate",
            "current_value": 35.0,
            "baseline": 8.0,
            "percentage_change": 337.5,
            "explanation": "Failure rate spiked on 2026-08-18",
        },
    ]

    with patch(
        "app.routers.anomalies.AnomalyDetectionService.detect_anomalies",
        new_callable=AsyncMock,
    ) as mock_detect:
        mock_detect.return_value = mock_anomalies
        response = await test_client.get("/api/anomalies/detect")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "unresolved_count" in data
        assert "critical_count" in data
        assert data["total"] == 2
        assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_anomaly_has_required_fields(test_client: AsyncClient):
    mock_anomalies = [
        {
            "type": "revenue_spike",
            "severity": "critical",
            "metric": "daily_revenue",
            "current_value": 50000.0,
            "baseline": 15000.0,
            "percentage_change": 233.33,
            "explanation": "Revenue spike detected",
        },
    ]

    with patch(
        "app.routers.anomalies.AnomalyDetectionService.detect_anomalies",
        new_callable=AsyncMock,
    ) as mock_detect:
        mock_detect.return_value = mock_anomalies
        response = await test_client.get("/api/anomalies/detect")
        data = response.json()
        item = data["items"][0]
        assert "type" in item
        assert "severity" in item
        assert "metric" in item
        assert "current_value" in item
        assert "baseline" in item
        assert "percentage_change" in item
        assert "explanation" in item
        assert item["severity"] == "critical"
