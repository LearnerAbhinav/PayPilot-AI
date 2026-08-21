from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_forecast_returns_data(test_client: AsyncClient):
    mock_forecast = {
        "current_balance": 450000.0,
        "forecast_days": 7,
        "daily_predictions": [
            {
                "date": "2026-08-21",
                "predicted_inflow": 25000.0,
                "predicted_outflow": 12000.0,
                "net_flow": 13000.0,
                "predicted_balance": 463000.0,
                "confidence": 0.82,
                "risk_level": "low",
            },
            {
                "date": "2026-08-22",
                "predicted_inflow": 24500.0,
                "predicted_outflow": 11500.0,
                "net_flow": 13000.0,
                "predicted_balance": 476000.0,
                "confidence": 0.80,
                "risk_level": "low",
            },
        ],
        "overall_confidence": 0.81,
        "overall_risk_level": "low",
        "assumptions": [
            "Forecast uses 7-day simple moving average with trend extrapolation",
        ],
    }

    with patch(
        "app.routers.forecast.ForecastService.forecast_cash_flow",
        new_callable=AsyncMock,
    ) as mock_fc:
        mock_fc.return_value = mock_forecast
        response = await test_client.get("/api/forecast/cash-flow?days=7")
        assert response.status_code == 200
        data = response.json()
        assert "current_balance" in data
        assert "daily_predictions" in data
        assert "overall_confidence" in data
        assert "overall_risk_level" in data
        assert data["forecast_days"] == 7


@pytest.mark.asyncio
async def test_forecast_has_confidence_levels(test_client: AsyncClient):
    mock_forecast = {
        "current_balance": 100000.0,
        "forecast_days": 14,
        "daily_predictions": [
            {
                "date": "2026-08-21",
                "predicted_inflow": 10000.0,
                "predicted_outflow": 5000.0,
                "net_flow": 5000.0,
                "predicted_balance": 105000.0,
                "confidence": 0.75,
                "risk_level": "low",
            },
        ],
        "overall_confidence": 0.75,
        "overall_risk_level": "low",
        "assumptions": [],
    }

    with patch(
        "app.routers.forecast.ForecastService.forecast_cash_flow",
        new_callable=AsyncMock,
    ) as mock_fc:
        mock_fc.return_value = mock_forecast
        response = await test_client.get("/api/forecast/cash-flow?days=14")
        data = response.json()
        assert "overall_confidence" in data
        assert isinstance(data["overall_confidence"], float)
        assert 0.0 <= data["overall_confidence"] <= 1.0

        for prediction in data["daily_predictions"]:
            assert "confidence" in prediction
            assert "risk_level" in prediction
            assert prediction["risk_level"] in ("low", "medium", "high", "critical")
