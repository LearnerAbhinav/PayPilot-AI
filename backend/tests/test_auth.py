import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.services.auth import AuthService


@pytest.mark.asyncio
async def test_register_user(test_client: AsyncClient):
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.merchant_id = uuid.uuid4()
    mock_user.role = "merchant_admin"

    with patch("app.routers.auth.AuthService.register_user", new_callable=AsyncMock) as mock_register:
        mock_register.return_value = mock_user
        response = await test_client.post(
            "/api/auth/register",
            json={
                "email": "new@paypilot.ai",
                "password": "securepass123",
                "full_name": "New User",
                "business_name": "New Business",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "merchant_admin"


@pytest.mark.asyncio
async def test_login_success(test_client: AsyncClient):
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.merchant_id = uuid.uuid4()
    mock_user.role = "merchant_admin"

    with patch("app.routers.auth.AuthService.authenticate_user", new_callable=AsyncMock) as mock_auth:
        mock_auth.return_value = mock_user
        response = await test_client.post(
            "/api/auth/login",
            json={
                "email": "test@paypilot.ai",
                "password": "password123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(test_client: AsyncClient):
    with patch("app.routers.auth.AuthService.authenticate_user", new_callable=AsyncMock) as mock_auth:
        from fastapi import HTTPException
        mock_auth.side_effect = HTTPException(
            status_code=401, detail="Invalid email or password"
        )
        response = await test_client.post(
            "/api/auth/login",
            json={
                "email": "test@paypilot.ai",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(test_client: AsyncClient):
    with patch("app.routers.auth.AuthService.authenticate_user", new_callable=AsyncMock) as mock_auth:
        from fastapi import HTTPException
        mock_auth.side_effect = HTTPException(
            status_code=401, detail="Invalid email or password"
        )
        response = await test_client.post(
            "/api/auth/login",
            json={
                "email": "nobody@paypilot.ai",
                "password": "password123",
            },
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authenticated(test_client: AsyncClient, test_merchant_id):
    response = await test_client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@paypilot.ai"
    assert data["role"] == "merchant_admin"


@pytest.mark.asyncio
async def test_get_me_unauthenticated(unauthenticated_client: AsyncClient):
    response = await unauthenticated_client.get("/api/auth/me")
    assert response.status_code in (401, 403)
