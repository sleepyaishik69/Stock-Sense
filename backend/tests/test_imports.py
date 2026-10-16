from io import BytesIO
import json
import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db import Base, get_db
from app.main import app


def test_csv_import_validation_and_duplicate_detection():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Testing = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    def override_db():
        db = Testing()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_db] = override_db
    content = b'transaction_id,date,sku,product_name,quantity,unit_price,discount,unit_cost\nT-1,2026-09-01,TEA-1,Black Tea,2,"1,250.00",0,700\nT-2,not-a-date,TEA-1,Black Tea,1,1250,0,700\nT-3,2026-09-03,EVIL,"=HYPERLINK(""https://example.org"",""open"")",1,15,0,5\n'
    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            assert client.post("/api/auth/register", json={"email":"importer@example.com","password":"long-password-123","workspace_name":"Import workspace","store_name":"Shop"}).status_code == 200
            preview = client.post("/api/imports/preview", files={"file":("sales.csv",content,"text/csv")})
            assert preview.status_code == 200
            mapping = preview.json()["suggested_mapping"]
            assert mapping["date"] == "date" and mapping["unit_price"] == "unit_price"
            imported = client.post("/api/imports/confirm", files={"file":("sales.csv",content,"text/csv")}, data={"mapping_json":json.dumps(mapping)})
            assert imported.status_code == 200
            assert imported.json()["imported_rows"] == 2
            assert imported.json()["rejected_rows"] == 1
            errors = client.get(f"/api/imports/{imported.json()['import_id']}/errors")
            assert "date" in errors.json()[0]["message"]
            duplicate = client.post("/api/imports/confirm", files={"file":("sales.csv",content,"text/csv")}, data={"mapping_json":json.dumps(mapping)})
            assert duplicate.json()["imported_rows"] == 0
            assert duplicate.json()["rejected_rows"] == 3
            report = client.post("/api/reports", params={"start":"2026-09-01","end":"2026-09-30"})
            assert report.status_code == 200 and report.headers["content-type"].startswith("text/csv")
            assert "'=HYPERLINK" in report.text
            tea = next(p for p in client.get("/api/products").json() if p["sku"] == "TEA-1")
            patched = client.patch(f"/api/products/{tea['id']}", json={"stock_on_hand":0,"unit_cost":700,"lead_time_days":2,"reorder_threshold":1})
            assert patched.status_code == 200
            plan = client.post("/api/analytics/budget-plan", params={"start":"2026-09-01","end":"2026-09-30"}, data={"budget":"10000"})
            assert plan.status_code == 200
            assert sum(x["estimated_purchase_cost"] for x in plan.json()["allocations"]) <= 10000
            assert plan.json()["budget_remaining"] >= 0
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)


def test_excel_preview_detects_columns():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Testing = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    def override_db():
        db = Testing()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_db] = override_db
    buf = BytesIO()
    pd.DataFrame([{"date":"2026-09-01","qty":2,"price":49.5}]).to_excel(buf,index=False)
    try:
        with TestClient(app) as client:
            client.post("/api/auth/register", json={"email":"excel@example.com","password":"long-password-123","workspace_name":"Excel workspace","store_name":"Shop"})
            response = client.post("/api/imports/preview", files={"file":("sales.xlsx",buf.getvalue(),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
            assert response.status_code == 200
            assert response.json()["suggested_mapping"]["quantity"] == "qty"
            assert response.json()["suggested_mapping"]["unit_price"] == "price"
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
