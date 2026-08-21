import uuid
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_dashboard_summary(test_client: AsyncClient):
    mock_summary = {
        "today": {"revenue": 12500.0, "total": 45, "successful": 42, "failed": 3},
        "this_week": {"revenue": 87500.0, "total": 310, "successful": 290, "failed": 20},
        "this_month": {"revenue": 350000.0, "total": 1250, "successful": 1180, "failed": 70},
        "revenue_change_pct": 12.5,
        "active_today": 45,
    }

    with patch(
        "app.routers.analytics.AnalyticsService.get_dashboard_summary",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = mock_summary
        response = await test_client.get("/api/analytics/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "today" in data
        assert "this_week" in data
        assert "this_month" in data
        assert "revenue_change_pct" in data
        assert data["today"]["revenue"] == 12500.0


@pytest.mark.asyncio
async def test_get_revenue_trend(test_client: AsyncClient):
    mock_trend = [
        {"date": "2026-08-19", "revenue": 15000.0},
        {"date": "2026-08-20", "revenue": 18500.0},
    ]

    with patch(
        "app.routers.analytics.AnalyticsService.get_revenue_trend",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = mock_trend
        response = await test_client.get("/api/analytics/revenue-trend?days=30")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["revenue"] == 15000.0


@pytest.mark.asyncio
async def test_get_payment_method_breakdown(test_client: AsyncClient):
    mock_breakdown = [
        {"method": "upi", "count": 450, "revenue": 225000.0, "success_rate": 96.5},
        {"method": "card", "count": 300, "revenue": 180000.0, "success_rate": 92.1},
    ]

    with patch(
        "app.routers.analytics.AnalyticsService.get_payment_method_breakdown",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = mock_breakdown
        response = await test_client.get("/api/analytics/payment-methods?days=30")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["method"] == "upi"
        assert data[0]["success_rate"] == 96.5


@pytest.mark.asyncio
async def test_period_comparison(test_client: AsyncClient):
    mock_comparison = {
        "current_period": {
            "total_transactions": 500,
            "successful_transactions": 470,
            "failed_transactions": 30,
            "total_revenue": 250000.0,
            "success_rate": 94.0,
            "avg_transaction": 531.91,
        },
        "previous_period": {
            "total_transactions": 450,
            "successful_transactions": 410,
            "failed_transactions": 40,
            "total_revenue": 210000.0,
            "success_rate": 91.11,
            "avg_transaction": 512.2,
        },
        "changes": {
            "revenue_change_pct": 19.05,
            "transaction_change_pct": 11.11,
            "success_rate_change": 2.89,
        },
    }

    with patch(
        "app.routers.analytics.AnalyticsService.compare_periods",
        new_callable=AsyncMock,
    ) as mock_compare:
        mock_compare.return_value = mock_comparison
        response = await test_client.get(
            "/api/analytics/compare"
            "?current_start=2026-07-01T00:00:00"
            "&current_end=2026-07-31T23:59:59"
            "&prev_start=2026-06-01T00:00:00"
            "&prev_end=2026-06-30T23:59:59"
        )
        assert response.status_code == 200
        data = response.json()
        assert "current_period" in data
        assert "previous_period" in data
        assert "changes" in data
        assert data["changes"]["revenue_change_pct"] == 19.05
