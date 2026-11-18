from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Load test settings BEFORE the app is imported: app.db creates the engine
# from DATABASE_URL at import time. Real environment variables (CI) win.
load_dotenv(BACKEND_DIR / ".env.test", override=False)

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import SessionLocal, engine, get_db
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def migrated_test_db():
    """Once per test run: refuse non-test databases, then migrate to head."""
    url = get_settings().database_url
    db_name = url.rsplit("/", 1)[-1].split("?")[0]
    assert db_name.endswith("_test"), f"Refusing to run tests against '{db_name}'"

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    command.upgrade(cfg, "head")


@pytest.fixture
def db_session():
    """A session inside a transaction that is rolled back after the test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    """A test client whose requests use the test's db_session."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
