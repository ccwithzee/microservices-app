import pytest
from fastapi.testclient import TestClient
from app.main import app, Base, engine, SessionLocal, User

client = TestClient(app)

# Recreate DB before each test run
@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_create_user():
    response = client.post("/users/", json={"username": "alice", "email": "alice@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "alice"
    assert data["email"] == "alice@example.com"
    assert "id" in data

def test_get_user():
    client.post("/users/", json={"username": "bob", "email": "bob@example.com"})
    response = client.get("/users/1")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "bob"

def test_update_user():
    client.post("/users/", json={"username": "carol", "email": "carol@example.com"})
    response = client.put("/users/1", json={"username": "carol_updated", "email": "carol@new.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "carol_updated"

def test_delete_user():
    client.post("/users/", json={"username": "dave", "email": "dave@example.com"})
    response = client.delete("/users/1")
    assert response.status_code == 200
    assert response.json() == {"message": "User deleted"}
    # Verify deleted
    response = client.get("/users/1")
    assert response.status_code == 404
