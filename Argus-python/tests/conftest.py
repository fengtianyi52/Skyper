import asyncio
import pytest
import pytest_asyncio

try:
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.dependencies import get_db, async_session_factory, engine
    INTEGRATION_DEPS_AVAILABLE = True
except Exception:
    # Offline evaluator tests intentionally do not need the full web stack.
    # Keep collection usable before `requirements.txt` is installed.
    INTEGRATION_DEPS_AVAILABLE = False


def pytest_collection_modifyitems(config, items):
    if INTEGRATION_DEPS_AVAILABLE:
        return
    skip = pytest.mark.skip(reason="FastAPI integration dependencies are not installed")
    for item in items:
        if item.name.startswith("test_") and "agent_regression" not in item.nodeid:
            item.add_marker(skip)


@pytest_asyncio.fixture
async def client():
    if not INTEGRATION_DEPS_AVAILABLE:
        pytest.skip("FastAPI integration dependencies are not installed")
    try:
        async with async_session_factory() as session:
            async def override_get_db():
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
            app.dependency_overrides[get_db] = override_get_db

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                yield ac
    finally:
        app.dependency_overrides.clear()
        # asyncpg connections are tied to the event loop that created them;
        # pytest-asyncio may use a fresh loop for the next test.
        await engine.dispose()


@pytest_asyncio.fixture
async def auth_headers(client):
    # Register test user
    resp = await client.post("/api/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "displayName": "Test User",
        "password": "Test@12345678",
    })
    # Login
    resp = await client.post("/api/auth/login", json={
        "loginId": "testuser",
        "password": "Test@12345678",
    })
    data = resp.json()
    token = data["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}
