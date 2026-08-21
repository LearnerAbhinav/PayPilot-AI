# PayPilot AI — Architecture Audit

**Date**: 21 Aug 2026  
**Auditor**: AI Engineering Review  
**Scope**: Full codebase — backend, frontend, database, AI agent, security, data integrity

---

## 1. Current Architecture

### Backend (Python / FastAPI)

```
backend/
├── app/
│   ├── main.py              # FastAPI app, CORS, lifespan, routes
│   ├── config.py             # Pydantic settings from .env
│   ├── database.py           # SQLAlchemy async engine, session factory
│   ├── agent/
│   │   ├── orchestrator.py   # AI agent — LLM tool-calling loop
│   │   └── prompts.py        # System prompt, templates
│   ├── models/               # 13 SQLAlchemy ORM models
│   ├── routers/              # 8 API routers
│   ├── schemas/              # 11 Pydantic schema files
│   ├── services/             # 7 business logic services
│   └── tools/                # 6 typed AI tools
├── scripts/
│   └── seed.py               # Demo data generator (random)
└── tests/                    # 7 test files + conftest
```

### Frontend (React / TypeScript / Vite)

```
frontend/src/
├── App.tsx                   # BrowserRouter, protected routes
├── api/                      # 9 API client modules (fetch-based)
├── components/               # 9 component directories
├── hooks/                    # Custom hooks
├── lib/utils.ts              # Formatting, currency, dates
├── pages/                    # 10 page components
└── types/                    # TypeScript interfaces
```

### Database (PostgreSQL 16)

- **ORM**: SQLAlchemy 2.x async
- **Tables**: users, merchants, customers, transactions, refunds, payment_methods, payment_failures, payouts, cash_flow_events, ai_conversations, ai_messages, ai_actions, audit_logs
- **Migrations**: None (uses `create_all` on startup)
- **Seed**: `scripts/seed.py` — uses `random`, not deterministic

---

## 2. Current Data Flow

```
Frontend (React)
    ↓ fetch(/api/*)
Vite Dev Proxy → FastAPI Backend
    ↓ JWT auth dependency
Router → Service → SQLAlchemy → PostgreSQL
    ↓
JSON Response → React state → Render
```

**AI Flow:**
```
User message → POST /api/ai/chat
    ↓
AIAgentOrchestrator.process_message()
    ↓
Build system prompt + conversation history
    ↓
Call LLM (OpenAI-compatible API)
    ↓
LLM returns tool_calls → execute tools → feed results back
    ↓ (up to 5 rounds)
Final LLM response → save to DB → return to frontend
    ↓
Audit event created
```

---

## 3. Existing Strengths

| Area | Assessment |
|------|-----------|
| **Data model** | Well-structured. 13 proper SQLAlchemy models with UUIDs, Numeric(15,2) for money, proper FKs, composite indexes |
| **Typed AI tools** | Good BaseTool ABC with ActionClass enum (READ_ONLY, REVERSIBLE, REQUIRES_APPROVAL, BLOCKED), input validation, authorization checks, safe_execute wrapper |
| **Agent orchestrator** | Real multi-round tool-calling loop (up to 5 rounds), proper error handling, conversation history loading/saving |
| **Audit logging** | AuditService.log_ai_action() records prompts, decisions, tools called, inputs, outputs |
| **Auth** | JWT + bcrypt password hashing, token validation, user-merchant relationship |
| **Frontend API client** | Clean fetch wrapper with token injection, error handling, query params |
| **UI quality** | Professional dark fintech design, loading states, skeletons, error states |
| **Seed data** | Creates ~15,000+ transactions over 90 days with intentional failure spikes (last 3 days have 2.5x failure multiplier) |
| **Financial math** | Uses Python `Decimal` in analytics calculations with ROUND_HALF_UP |
| **Anomaly detection** | Real z-score based detection (revenue, failure rate, refund rate) with 14-day sliding window |
| **Cash flow forecast** | Moving average + trend extrapolation with confidence scoring |

---

## 4. Existing Weaknesses & Production Gaps

### 4.1 Hardcoded / Mock Data in Frontend

| File | Problem |
|------|---------|
| `DashboardPage.tsx:37-43` | `generateSparkline()` — mock random sparkline data, not from backend |
| `DashboardPage.tsx:194-199` | `change={12.5}` — hardcoded percentage changes on MetricCards |
| `DashboardPage.tsx:205-209` | `change={8.2}`, `change={-1.2}`, `change={5.4}` — all hardcoded |
| `DashboardPage.tsx:138` | `healthScore = successRate - (anomalies.length * 2)` — meaningless formula |
| `DashboardPage.tsx:279` | "Merchant Health" card with arbitrary score |
| `DashboardPage.tsx:417-443` | Live activity ticker — completely hardcoded fake transactions (₹4,500 UPI, ₹1,250 Card, ₹8,900 Netbanking) |
| `AuditPage.tsx:75-78` | "Trust Score: 100/100" — always shows 100/100, no calculation |

### 4.2 Data Consistency Problems

| Problem | Details |
|---------|---------|
| Dashboard metrics don't show period-over-period changes | `change` values on MetricCards are hardcoded, not computed from `compare_periods()` |
| Anomalies page data shape mismatch | Frontend expects `items[]` with `id` and `detected_at`, but backend returns flat `list[dict]` without `id` or `detected_at` |
| Audit log field mapping broken | Frontend expects `user`, `entity_type`, `entity_id`, `details` as strings, but backend stores `user_id` (UUID), `resource_type`, `resource_id`, `details` (JSONB) |
| Actions page field mapping | Frontend expects `status` field, backend uses `approval_status` |
| Copilot message shape mismatch | Frontend expects `{id, message, response}`, backend returns `{conversation_id, message: {id, role, content, tools_called}}` |

### 4.3 Non-Deterministic Seed Data

- `seed.py` uses `random.random()` and `random.choice()` without a fixed seed
- `MERCHANT_ID = uuid.uuid4()` — new UUID every run
- Cannot reproduce the same demo scenario twice
- Customer names are generic: "Customer 0001", "Customer 0002"

### 4.4 Action System is Incomplete

- `SimulatePaymentRecoveryTool` calculates eligible transactions but **never calls `AIActionService.create_action()`** — the action is computed but not persisted
- `AIActionService.execute_action()` immediately sets status to "completed" with no actual simulation logic — just `{"status": "success"}`
- No before/after impact calculation
- No verification step
- No state machine (missing PROPOSED, PENDING_APPROVAL, EXECUTING, VERIFIED, REJECTED, FAILED states)

### 4.5 Recovery Policy Engine Missing

- Recovery strategy is a flat 30% estimate: `estimated_recoverable = total_failed_amount * Decimal("0.30")`
- Retry eligibility is a flat 35%: `estimated_recovery = total_eligible_amount * Decimal("0.35")`
- No per-transaction evaluation (customer history, failure type, retry count, amount)
- No multiple strategies (retry, notify, alternative method)
- No policy configuration

### 4.6 AI Investigation System Missing

- No dedicated investigation model or service
- No investigation page in frontend
- No evidence-gathering workflow
- AI responses are unstructured LLM text, not structured tool-execution displays

### 4.7 Security Issues

| Issue | Location | Severity |
|-------|----------|----------|
| **Request headers logged** | `main.py:57` — logs ALL request headers including Authorization tokens | HIGH |
| **No rate limiting** | No rate limiting on any endpoint, including auth | MEDIUM |
| **Tenant isolation gap in actions** | `actions.py:47-53` — approve_action checks merchant_id AFTER mutation | HIGH |
| **Tenant isolation gap in actions** | `actions.py:62-68` — execute_action checks merchant_id AFTER getting action | HIGH |
| **JWT secret in code** | `config.py:8` — default secret in source code | MEDIUM |
| **No CSRF protection** | No CSRF tokens for state-changing operations | LOW |
| **ProtectedRoute is client-side only** | `App.tsx:14-17` — checks localStorage token existence, doesn't validate | LOW |

### 4.8 Missing Tests

- No test for action approval/execution
- No test for tenant isolation
- No test for recovery strategy
- No end-to-end test
- No test for audit logging
- Existing tests use in-memory SQLite (may not match PostgreSQL behavior)

### 4.9 No Migrations

- `init_db()` calls `Base.metadata.create_all()` 
- No Alembic migrations
- Schema changes require dropping and recreating all tables

### 4.10 Frontend-Backend Contract Mismatches

The TypeScript types in `frontend/src/types/index.ts` don't match the Pydantic schemas:
- `TransactionListResponse` expects `transactions[]` but backend sends `items[]`
- `ActionResponse` expects `status` but backend has `approval_status` + `execution_status`
- `AuditLogEntry` expects string `user`, `details` but backend has UUID `user_id`, JSONB `details`
- `ChatResponse` expects `{message, response}` but backend returns structured `{message: MessageResponse}`

### 4.11 Performance

- Analytics service loads ALL transactions into Python memory for computation
- No server-side aggregation (GROUP BY) — iterates in Python
- Anomaly detection loads 60 days of all transactions
- No caching

---

## 5. Recommended Architecture

### Target State

```
┌─────────────────────────────────────────────────────┐
│                    FRONTEND (React)                  │
│  Dashboard │ Investigations │ Copilot │ Actions     │
│  Transactions │ Analytics │ Anomalies │ Audit       │
└────────────────────┬────────────────────────────────┘
                     │ /api/*
┌────────────────────▼────────────────────────────────┐
│                   FASTAPI BACKEND                    │
│                                                      │
│  ┌─────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ Routers │→ │ Services │→ │ Database (PG)     │  │
│  └─────────┘  └──────────┘  └───────────────────┘  │
│       │                                              │
│  ┌────▼──────────────────────────────────────────┐  │
│  │              AI ORCHESTRATOR                    │  │
│  │  Intent → Tool Selection → Execution → LLM    │  │
│  └────────────────────┬──────────────────────────┘  │
│                       │                              │
│  ┌────────────────────▼──────────────────────────┐  │
│  │              TYPED TOOLS (existing)            │  │
│  │  + InvestigationTools                          │  │
│  │  + RecoveryPolicyEngine                        │  │
│  │  + ActionExecutionEngine                       │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │          RECOVERY POLICY ENGINE                │  │
│  │  Per-txn evaluation → Strategy → Impact calc  │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │          ACTION SYSTEM (state machine)         │  │
│  │  PROPOSED → PENDING → APPROVED → EXECUTING    │  │
│  │  → EXECUTED → VERIFIED / REJECTED / FAILED    │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │          AUDIT SYSTEM (event sourcing)         │  │
│  │  Every AI/human/system action → audit event    │  │
│  └───────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

---

## 6. Implementation Phases

### Phase 0 — Audit ✅ (this document)

### Phase 1 — Data Foundation
- Fix seed.py to be deterministic (fixed seed, fixed UUIDs)
- Fix frontend-backend contract mismatches
- Remove hardcoded metrics from Dashboard
- Remove fake Trust Score
- Remove mock sparklines and live ticker
- Compute real period-over-period changes
- Add `GET /api/dashboard/summary` with computed metrics

### Phase 2 — AI Investigation System
- Add Investigation model & service
- Add investigation tools
- Create Investigation page in frontend
- Show tool execution steps (not chain-of-thought)
- Evidence gathering and root-cause display

### Phase 3 — Recovery Policy Engine
- Per-transaction recovery eligibility evaluation
- Failure taxonomy (UPI_TIMEOUT, BANK_UNAVAILABLE, etc.)
- Multiple strategies (retry, notify, alt payment method)
- Recoverable revenue calculation from real data
- Policy-based recommendations

### Phase 4 — Action System
- Full state machine (PROPOSED → VERIFIED)
- Human-in-the-loop approval UI
- Simulated execution with deterministic outcomes
- Before/after impact calculation
- Verification step

### Phase 5 — Audit System
- Real audit events for every AI and human action
- Filterable audit log (by actor, type, date)
- Action trace (investigation → recommendation → approval → execution → verification)
- Remove fake Trust Score, replace with real metrics

### Phase 6 — UI Transformation
- Dashboard: Payment Operations Command Center with AI insight panel
- Copilot: Proactive agent with monitoring signals (not generic chatbot)
- Actions: Real pending actions with approval workflow
- Anomalies: Actionable anomalies with investigate/recover buttons
- Cash Flow: Connected to recovery actions

### Phase 7 — Security & Quality
- Fix header logging (remove Authorization from logs)
- Fix tenant isolation in action approval/execution (check BEFORE mutation)
- Add rate limiting
- Fix all contract mismatches
- Add missing tests

### Phase 8 — Final Demo
- Deterministic 5-minute demo scenario
- End-to-end flow test
- Documentation

---

## 7. Priority Order

```
40% Backend + Data (Phases 1, 3, 4)
25% AI Agent + Tools (Phase 2)
15% Recovery Policy Engine (Phase 3)
10% Safety + Audit (Phases 5, 7)
10% UI polish (Phase 6)
```
