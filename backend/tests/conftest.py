import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["SECRET_KEY"] = "test-secret"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import User
from app.security import hash_password


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db() -> Session:
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def client():
    return TestClient(app)


def _make_user(db: Session, email: str, role: str, password: str = "Password123!") -> User:
    u = User(
        email=email,
        name=email.split("@")[0],
        password_hash=hash_password(password),
        role=role,
        status="active",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def admin_user(db):
    return _make_user(db, "admin@test.com", "admin")


@pytest.fixture
def manager_user(db):
    return _make_user(db, "manager@test.com", "manager")


@pytest.fixture
def operator_user(db):
    return _make_user(db, "op@test.com", "operator")


def _login(client: TestClient, email: str, password: str = "Password123!") -> str:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["data"]["tokens"]["access_token"]


@pytest.fixture
def admin_token(client, admin_user):
    return _login(client, admin_user.email)


@pytest.fixture
def manager_token(client, manager_user):
    return _login(client, manager_user.email)


@pytest.fixture
def operator_token(client, operator_user):
    return _login(client, operator_user.email)


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
