from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db import Base, get_db
from app.main import app


def test_workspace_data_is_scoped():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Testing = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    def override_db():
        db = Testing()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            a = client.post("/api/auth/register", json={"email":"a@example.com","password":"long-password-123","workspace_name":"A workspace","store_name":"A store"})
            assert a.status_code == 200
            assert client.get("/api/stores").json()[0]["name"] == "A store"
            client.post("/api/auth/logout")
            b = client.post("/api/auth/register", json={"email":"b@example.com","password":"long-password-123","workspace_name":"B workspace","store_name":"B store"})
            assert b.status_code == 200
            assert [s["name"] for s in client.get("/api/stores").json()] == ["B store"]
            assert client.get("/api/analytics/overview", params={"store_id":1}).status_code == 404
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
