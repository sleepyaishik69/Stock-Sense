# StockSense AI

StockSense is a retail analytics MVP with a Next.js dashboard, FastAPI service, relational storage, deterministic money calculations, flexible CSV/Excel import, and an optional local Gemma explanation endpoint. Its data flow keeps calculations in Python and gives Ollama only a bounded aggregate facts payload.

## What's implemented

- Workspace registration/login with a signed HttpOnly session cookie; products, stores, sales, and imports are queried under the authenticated workspace.
- SQLite for local development and PostgreSQL via Docker Compose.
- New registrations create an empty workspace and first store. No products or sales are seeded; users can add products or import their own records.
- CSV/Excel preview with header suggestion, required field checks, explicit confirm, duplicate fingerprint detection, new-product creation, partial import, and row error records.
- Fixed-precision decimal sales totals rounded half-up to cents. Net sales = gross sales − discounts − refunds; tax is excluded. Gross profit = net sales − COGS only if all selected sale lines have cost. Margin is null when cost is incomplete or net sales is zero. Transaction count is distinct transaction IDs.
- Product ranking, dated daily sales series, low-stock alerts, recent-average reorder suggestions, current-cost inventory valuation, and CSV report export.
- A daily action center with evidence-based stockout/reorder review prompts and data-quality tasks for unknown stock or missing product costs.
- An append-only stock movement ledger for opening counts, physical counts, deliveries, damage, and corrections, with workspace-scoped history. Historical sales imports do not silently overwrite today's stock.
- A deterministic budget planner that allocates only against supported reorder suggestions with known costs and stock, and never places orders.
- Basket co-purchase support/confidence/lift and excess-stock candidates when uploaded transaction IDs and stock data support them; these are testable patterns, not causal claims.
- Ollama status and Gemma 2 2B structured insight/chat calls; non-AI dashboard and reports work when Ollama is unavailable.
- Responsive dashboard with Overview, Sales Analytics, Products, Inventory, Finance, Marketing, Ask StockSense, Reports, Imports and Settings views.
- Unit tests for sales, discount, return, zero-denominator and missing-cost behavior; an API test exercises workspace scoping.

## Local setup

### API

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API docs: <http://localhost:8000/docs>. On startup the API creates an empty local SQLite schema with no user or business rows. PostgreSQL deployments apply the Alembic migration.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>, create a workspace with your business name and first store, then import your own sales file or add products. Existing users can switch to sign in.

### Gemma 2 2B through Ollama

Install Ollama for your operating system, then run:

```powershell
ollama pull gemma2:2b
ollama serve
```

The default API address is `http://localhost:11434`. Check `/api/ai/status`; the dashboard displays connection state. Common totals and rankings use core analytics directly. Other questions use Gemma when it is available and fall back to a labeled summary of calculated facts if it is not. AI-generated insights require the model; analytics do not. With Compose, start the optional service using `docker compose --profile ai up --build`; then run `docker compose exec ollama ollama pull gemma2:2b`.

## PostgreSQL / Compose

Copy `.env.example` to `.env`, replace `SECRET_KEY`, then run `docker compose up --build`. Open port 3000 for the app and port 8000 for API docs. The Compose database credentials are development-only. For a real deployment, use a managed secret store, TLS, a restricted application database role, backups, and an Alembic migration workflow.

An initial Alembic migration is included. Local SQLite creates its empty schema on first startup; PostgreSQL deployments apply migrations before launching the API. `backend/schema.sql` is the generated SQLite schema snapshot and contains no business data. Alembic migrations remain the source of truth for deployments. PostgreSQL RLS policies are not yet enabled. Application queries enforce workspace scoping, but this is not yet the database-enforced tenant boundary required for production.

## Import workflow

Supported canonical import fields are date, quantity, and unit price (required); transaction ID, SKU, product name, category, discount, tax, unit cost, and return indicator are optional. Header aliases are suggested automatically. Current UI confirms the suggested mapping; direct API clients can send an explicit mapping object. Rows with invalid dates/numbers, non-positive quantities, or duplicates are returned in the row error report. Mark returns using a return column; negative quantities are rejected to avoid treating refunds as sales. The backend accepts files up to 15 MB by default.

Example CSV:

```csv
transaction_id,date,sku,product_name,quantity,unit_price,discount,unit_cost,return
T-100,2026-09-01,TEA-1,Black tea,2,180,10,95,false
T-101,2026-09-02,TEA-1,Black tea,1,180,0,95,true
```

## Tests

```powershell
cd backend
pytest -q
```

## Known limitations

- This is an MVP foundation, not the complete production platform in the supplied specification. The implementation does not yet include RLS, multi-user workspace membership/roles, password reset, CSRF defenses, request rate limiting, audit history, confirmed purchase orders, supplier management, historical cost snapshots, optimized budget planning, promotion analysis, PDF reports, Excel exports, retention/delete controls, or automated E2E/browser tests.
- Quantities are whole units; locale-specific decimal-comma monetary formats are not supported. Monetary imports expect a period decimal mark and may include currency symbols or comma thousands separators.
- Reorder quantities are transparent averages over the selected period plus lead-time demand and the configured threshold. They do not model variability, seasonality, pack sizes, expiry, or incoming orders. Treat them as review prompts, not purchase orders.
- Product import does not set stock from the sales file. Missing stock is unknown, not zero; record an opening count from Inventory before relying on reorder estimates.
- The stock movement ledger records changes from the point of entry onward; earlier inventory history cannot be reconstructed from sales imports alone.
- Common ranking and total questions are calculated directly from the selected data. Other questions send a bounded aggregate analysis context to Ollama; the UI labels whether Gemma or core analytics produced the answer and displays supporting product/inventory records. The model has no SQL or mutation tools.
- Session cookie `secure` is disabled for local HTTP; production deployment needs HTTPS configuration.
- Financial output is business analysis, not formal accounting, tax, or professional financial advice.

## Future roadmap

1. Add production password/session lifecycle, CSRF controls, roles, PostgreSQL RLS policies, and cross-tenant isolation tests.
2. Complete staged import mapping correction and exportable row error files; add Excel support tests, formula-safe spreadsheet export, and larger streaming imports.
3. Add supplier records, purchase orders with partial receiving, historical cost batches, stock snapshots, expiry tracking, seasonality-aware demand, and budget-constrained reorder allocation.
4. Add promotion baselines when reliable identifiers and comparison periods are present; provide PDF/Excel report generation.
5. Add registered analytics operations for question parsing, rate limits, concurrency bounds, model/prompt version logs, stronger factuality evaluation, and browser E2E coverage.
6. Add subscription/billing, multi-store comparisons, collaboration, data retention controls, deployment monitoring, and backup/restore automation.
