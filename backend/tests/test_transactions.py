import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from httpx import AsyncClient


MOCK_TX_ID = uuid.uuid4()


def _make_transaction(status="captured"):
    tx = MagicMock()
    tx.id = MOCK_TX_ID
    tx.merchant_id = uuid.uuid4()
    tx.customer_id = None
    tx.amount = 1500.00
    tx.currency = "INR"
    tx.status = status
    tx.payment_method = "upi"
    tx.payment_gateway = "razorpay"
    tx.failure_code = "insufficient_funds" if status == "failed" else None
    tx.failure_reason = "Insufficient funds" if status == "failed" else None
    tx.description = "Test payment"
    tx.metadata_json = None
    tx.created_at = datetime.utcnow()
    tx.updated_at = datetime.utcnow()
    return tx


@pytest.mark.asyncio
async def test_list_transactions(test_client: AsyncClient):
    mock_txns = [_make_transaction() for _ in range(3)]

    with patch(
        "app.routers.transactions.TransactionService.get_transactions",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = mock_txns
        with patch(
            "app.routers.transactions.TransactionService.count_transactions",
            new_callable=AsyncMock,
        ) as mock_count:
            mock_count.return_value = 3
            response = await test_client.get("/api/transactions/")
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total" in data
            assert "page" in data
            assert "total_pages" in data
            assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_get_transaction_by_id(test_client: AsyncClient):
    mock_tx = _make_transaction()

    with patch(
        "app.routers.transactions.TransactionService.get_transaction",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = mock_tx
        response = await test_client.get(f"/api/transactions/{MOCK_TX_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "captured"
        assert data["payment_method"] == "upi"


@pytest.mark.asyncio
async def test_filter_by_status(test_client: AsyncClient):
    mock_txns = [_make_transaction(status="failed") for _ in range(2)]

    with patch(
        "app.routers.transactions.TransactionService.get_transactions",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = mock_txns
        with patch(
            "app.routers.transactions.TransactionService.count_transactions",
            new_callable=AsyncMock,
        ) as mock_count:
            mock_count.return_value = 2
            response = await test_client.get("/api/transactions/?status=failed")
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 2
            assert all(item["status"] == "failed" for item in data["items"])


@pytest.mark.asyncio
async def test_get_failed_transactions(test_client: AsyncClient):
    mock_txns = [_make_transaction(status="failed") for _ in range(5)]

    with patch(
        "app.routers.transactions.TransactionService.get_failed_transactions",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = mock_txns
        response = await test_client.get("/api/transactions/failed?days=7")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 5
        assert all(tx["status"] == "failed" for tx in data)
