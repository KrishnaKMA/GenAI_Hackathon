# ClaimShield — AI Insurance Fraud Detection

**Stack:** FastAPI + React + IBM watsonx.ai + GraphSAGE GNN + Isolation Forest

---

## Quick Start (works right now, no teammate input needed)

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env          # Only JWT_SECRET needed for dev
python ../scripts/seed_demo.py # Loads demo data (run from backend/)
uvicorn main:app --reload     # Runs at localhost:8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev                   # Runs at localhost:5173
```

Login: `admin` / `admin123`
API docs: http://localhost:8000/docs
Demo button: Dashboard → "Demo Scenarios" → Click any risk level

---

## Generate JWT keys (Krishna does this once, optional for dev)

```bash
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -pubout -out public.pem
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Paste outputs into .env as JWT_PRIVATE_KEY, JWT_PUBLIC_KEY, FERNET_KEY
```

Without these keys, the app uses HS256 JWT fallback — fine for development.

---

## 👋 Teammate A — Plugging in ML Models

**You only need to touch ONE file:** `backend/services/ml_interface.py`

### Step 1 — Put your trained files here:
```
backend/models/gnn/pretrained/weights.pt    ← your GraphSAGE weights
backend/models/anomaly/iforest.pkl          ← your pickled IForest
```

### Step 2 — Open `ml_interface.py` and find these two functions:
```python
async def _real_analysis(claim_data: dict) -> FraudAnalysisResult:
    # ↓ TEAMMATE A: REPLACE THIS ENTIRE FUNCTION BODY
```

Fill them in. The file has detailed comments for every step.

### Step 3 — Verify it's working:
```bash
# Terminal (from backend/)
curl -X POST http://localhost:8000/analyze/CLAIM_A3F9B7K2 \
  -H "Authorization: Bearer $(curl -s -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | python -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')"

# Logs should show:
# [ML] ✅ Model files found — using REAL model
```

### What your `_real_analysis()` receives:
```python
claim_data = {
    "claim_token": "CLAIM_A3F9",     # already anonymized
    "claim_amount": 47500.0,
    "claim_type": "auto_repair",
    "prior_claim_count": 3,
    "days_since_last_claim": 45,
    "claimant_token": "CLAIMANT_A3F9",
    "provider_token": "PROVIDER_D4N1",
    "repair_shop_token": "SHOP_F2Q7",
    "incident_date": "2024-01-15",
    "filing_date": "2024-01-16",
    "adjuster_id": "adj_001",
}
```

### What your function must return:
See `FraudAnalysisResult` in `backend/models/schemas.py`. All fields documented.

### Graph helpers available:
```python
# backend/services/graph_builder.py
from services.graph_builder import get_entity_neighbors, build_adjacency_list, build_node_features
```

**DO NOT** touch the frontend, routes, or any other file.

---

## 👋 Teammate B — Plugging in IBM Credentials

**You only need to touch ONE file:** `backend/services/ibm_interface.py`

### Step 1 — Fill in `.env`:
```
WATSONX_API_KEY=      ← IBM Cloud → IAM → API Keys
WATSONX_PROJECT_ID=   ← watsonx.ai → Your Project → Manage → General
WATSONX_URL=https://us-south.ml.cloud.ibm.com
DB2_DSN=              ← IBM Cloud → Db2 → Service Credentials → dsn
```

### Step 2 — Open `ibm_interface.py` and fill in 3 functions:
```python
async def _real_narrative(analysis)            # → Granite LLM call
async def _real_log_factsheet(token, analysis) # → watsonx.governance write
async def _real_get_factsheets(limit)          # → watsonx.governance read
```

Each function has example code in the comments.

### Step 3 — Verify Granite works:
```bash
curl -X POST http://localhost:8000/analyze/demo/CRITICAL \
  -H "Authorization: Bearer <your_token>"
# Logs should show: [IBM] ✅ IBM credentials found — using REAL watsonx
# Narrative in response should be AI-generated, not hardcoded
```

### Step 4 — Set up Db2 tables:
```bash
cd backend
python scripts/setup_db2.py
# Creates: users, claims, entities, graph_edges, inference_log, tasks
```

**DO NOT** touch the frontend or ML files.

---

## Architecture

```
ClaimShield/
├── backend/
│   ├── main.py                     ← FastAPI app + startup
│   ├── models/
│   │   ├── schemas.py              ← All Pydantic types (CONTRACT)
│   │   ├── gnn/pretrained/         ← weights.pt goes here (Teammate A)
│   │   └── anomaly/                ← iforest.pkl goes here (Teammate A)
│   ├── core/
│   │   ├── security.py             ← JWT, bcrypt, Fernet, TOTP
│   │   ├── database.py             ← SQLite → Db2 abstraction
│   │   └── exceptions.py           ← HTTP error classes
│   ├── services/
│   │   ├── ml_interface.py         ← ← TEAMMATE A edits this
│   │   ├── ibm_interface.py        ← ← TEAMMATE B edits this
│   │   ├── agent_interface.py      ← Fraud agent (4 steps)
│   │   ├── claim_ingestor.py       ← PII tokenization pipeline
│   │   ├── graph_builder.py        ← Graph helpers for GNN
│   │   └── report_generator.py     ← Combines ML + IBM → report
│   └── api/routes/
│       ├── auth.py                 ← POST /auth/login
│       ├── claims.py               ← GET/POST /claims, GET /factsheets
│       ├── analysis.py             ← POST /analyze/:token
│       ├── agent.py                ← WS /ws/agent/:token
│       └── admin.py                ← Admin CRUD
├── frontend/
│   └── src/
│       ├── App.tsx                 ← Router + auth guard + layout
│       ├── types/index.ts          ← TypeScript interfaces (mirrors schemas.py)
│       ├── lib/
│       │   ├── api.ts              ← Axios API client
│       │   ├── mockData.ts         ← Perfect mock ring data
│       │   ├── cytoscapeConfig.ts  ← Graph styling
│       │   └── utils.ts            ← Color helpers + formatters
│       ├── components/
│       │   ├── FraudGraph.tsx      ← Cytoscape entity graph
│       │   ├── TimelineSlider.tsx  ← Date filter for graph
│       │   ├── FraudScoreBadge.tsx ← Score display (pulses for CRITICAL)
│       │   ├── InvestigatorReport.tsx ← Full report (4 tabs)
│       │   ├── AgentStatus.tsx     ← Live 4-step agent panel
│       │   ├── ClaimsTable.tsx     ← Paginated claims list
│       │   ├── FactsheetPanel.tsx  ← IBM governance audit trail
│       │   └── RedTeamMode.tsx     ← Demo scenario buttons
│       └── pages/
│           ├── LoginPage.tsx
│           ├── DashboardPage.tsx
│           ├── ClaimsPage.tsx
│           ├── ReportPage.tsx
│           └── SubmitClaimPage.tsx
├── data/seed_data/                 ← JSON demo data
├── scripts/
│   ├── seed_demo.py                ← Load demo data into SQLite
│   └── setup_db2.py                ← Create tables in IBM Db2
└── docker-compose.yml
```

---

## API Reference (auto-documented)

Full interactive docs at http://localhost:8000/docs

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /auth/login | — | Get JWT token |
| GET | /auth/me | ✓ | Current user |
| GET | /claims | ✓ | List all claims |
| POST | /claims | ✓ | Submit new claim |
| GET | /claims/{token} | ✓ | Get claim details |
| POST | /analyze/{token} | ✓ | Run fraud analysis |
| POST | /analyze/demo/{level} | ✓ | Demo analysis (LOW/MEDIUM/HIGH/CRITICAL) |
| GET | /factsheets | ✓ | IBM governance log |
| WS | /ws/agent/{token} | — | Stream agent steps |
| GET | /admin/stats | ADMIN | System statistics |
| GET | /admin/users | ADMIN | User management |

---

## Mock → Real switchover

| Component | Condition | What changes |
|-----------|-----------|-------------|
| ML Models | `weights.pt` + `iforest.pkl` exist | `[ML] ✅` in logs |
| IBM watsonx | `WATSONX_API_KEY` in `.env` | `[IBM] ✅` in logs |
| Database | `DB2_DSN` in `.env` | SQLite → Db2 |
| JWT | `JWT_PRIVATE_KEY` in `.env` | HS256 → RS256 |
| PII Encryption | `FERNET_KEY` in `.env` | Hash → Reversible |

---

## Docker (optional)

```bash
docker compose up --build
# Frontend: http://localhost:5173
# API:      http://localhost:8000/docs
```
