"""Shared test fixtures."""
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Patch loguru file sink before importing app (avoids PermissionError on root-owned logs)
import loguru
_original_add = loguru.logger.add
loguru.logger.add = lambda *a, **kw: 0

from app.database import Base, get_db
from app.main import app

# Restore original logger.add
loguru.logger.add = _original_add


@pytest.fixture
def db_session():
    """Create a fresh SQLite in-memory database session for each test."""
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    # Ensure models are imported so tables are registered in metadata
    from app.models.download import Download  # noqa: F401
    from app.models.settings import Setting  # noqa: F401
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """Provide a TestClient with the database dependency overridden."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    from fastapi.testclient import TestClient
    with patch('app.main.init_db'):
        with TestClient(app) as test_client:
            yield test_client
    app.dependency_overrides.clear()
