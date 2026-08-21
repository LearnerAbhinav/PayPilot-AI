<div align="center">

# PayPilot AI

**Autonomous AI Financial Operations Agent for Online Merchants**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-6-3178C6?style=flat&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)](https://docker.com)

</div>

---

## Problem Statement

Indian online merchants processing through payment gateways like Razorpay face fragmented visibility into their financial health. Failed transactions go unnoticed, cash flow surprises cause operational crises, and revenue leaks compound silently. Existing dashboards show historical data but lack the ability to **reason about** patterns, **predict** future issues, or **take autonomous action** to prevent losses.

A merchant with 10,000 monthly transactions might lose ₹5-8 lakhs to unrecovered failed payments, undetected anomalies, and poor cash flow timing — losses that compound month over month.

---

## Solution

PayPilot AI is an autonomous financial operations agent that goes beyond traditional dashboards. Instead of requiring merchants to interpret charts and manually investigate issues, PayPilot's AI agent:

1. **Continuously monitors** payment data across revenue, failures, refunds, and cash flow
2. **Reasons about** patterns using an LLM-powered agent with domain-specific tools
3. **Detects anomalies** using statistical methods (Z-score analysis with rolling windows)
4. **Forecasts** cash flow using trend extrapolation with confidence intervals
5. **Takes autonomous action** with human-in-the-loop approval for financial operations

The agent operates on a tool-use paradigm — it calls structured tools to gather evidence, analyzes results, and formulates data-backed recommendations. It never fabricates data; every claim is grounded in tool execution results.

---

## Why AI? — Not Just a Chatbot

PayPilot is an **agentic system**, not a conversational assistant. The distinction matters:

| Feature | Chatbot Approach | PayPilot Agent Approach |
|---|---|---|
| **Data Access** | RAG over docs | 11 structured tools querying live database |
| **Reasoning** | Pattern matching | Multi-step reasoning with evidence gathering |
| **Action** | Text suggestions | Creates auditable action plans with approval workflow |
| **Accuracy** | Hallucination-prone | Tool-grounded: numbers come from DB queries |
| **Autonomy** | Requires explicit questions | Proactively detects and flags issues |
| **Accountability** | No audit trail | Full audit log of every agent decision |

The agent uses a **ReAct-style loop**: Observe (call tools) → Think (analyze data) → Act (recommend or create action plan). This loop runs up to 5 rounds per query, allowing the agent to cross-reference multiple data sources before forming conclusions.

---

## Architecture

```mermaid
graph TB
    subgraph Frontend["Frontend (React + Vite + TypeScript)"]
        UI[Dashboard & Pages]
        Chat[Copilot Chat Interface]
    end

    subgraph Backend["Backend (FastAPI + Python 3.12)"]
        API[REST API Layer]
        Auth[JWT Authentication]
        
        subgraph Agent["AI Agent Orchestrator"]
            LLM[LLM Provider<br/>OpenAI GPT-4o]
            Tools[Tool Registry<br/>11 Domain Tools]
            Loop[ReAct Loop<br/>Max 5 Rounds]
        end
        
        subgraph Services["Service Layer"]
            TS[Transaction Service]
            AS[Analytics Service]
            FS[Forecast Service]
            ADS[Anomaly Detection<br/>Z-Score Analysis]
            AIS[AI Action Service]
            AUD[Audit Service]
        end
    end

    subgraph Database["PostgreSQL 16"]
        DB[(Merchants, Users,<br/>Transactions, Refunds,<br/>Cash Flow, AI Actions,<br/>Audit Logs)]
    end

    UI -->|REST API| API
    Chat -->|/api/ai/chat| API
    API --> Auth
    API --> Services
    API --> Agent
    Agent --> LLM
    Agent --> Tools
    Tools --> Services
    Services --> DB
    Agent --> AIS
    Agent --> AUD
```

---

## Agent Workflow

```mermaid
sequenceDiagram
    actor Merchant
    participant UI as Frontend
    participant API as FastAPI
    participant Orch as Agent Orchestrator
    participant LLM as GPT-4o
    participant Tools as Tool Registry
    participant DB as PostgreSQL

    Merchant->>UI: "Why did my revenue drop yesterday?"
    UI->>API: POST /api/ai/chat
    API->>Orch: process_message()
    
    Note over Orch: Round 1: Gather evidence
    Orch->>LLM: System prompt + user message + tool definitions
    LLM-->>Orch: tool_call: get_revenue_trend
    Orch->>Tools: execute(get_revenue_trend, days=30)
    Tools->>DB: SELECT transactions WHERE status='captured'
    DB-->>Tools: Transaction rows
    Tools-->>Orch: Revenue trend data
    Orch->>LLM: Tool result
    
    Note over Orch: Round 2: Cross-reference
    LLM-->>Orch: tool_call: detect_anomalies
    Orch->>Tools: execute(detect_anomalies)
    Tools->>DB: Z-score analysis on daily revenue
    DB-->>Tools: Anomaly results
    Tools-->>Orch: Anomaly detection results
    Orch->>LLM: Tool result
    
    Note over Orch: Round 3: Formulate response
    LLM-->>Orch: "Revenue dropped 22% due to..."
    
    Orch->>DB: Save conversation messages
    Orch->>DB: Log audit trail
    Orch-->>API: Response with evidence
    API-->>UI: ChatResponse
    UI-->>Merchant: Evidence-backed analysis + recommendations
```

---

## Features

### Dashboard
- **Real-time metrics**: Today's revenue, transactions, success rate
- **Period comparisons**: Week-over-week, month-over-month trends
- **Payment method breakdown**: UPI, cards, netbanking performance
- **Revenue trend charts**: 7/30/90 day configurable views

### AI Agent (Copilot)
- **Natural language queries**: Ask questions in plain English
- **Tool-augmented reasoning**: Agent calls 11 domain-specific tools
- **Multi-round conversations**: Maintains context across messages
- **Evidence-backed responses**: Every claim grounded in database queries
- **Proactive suggestions**: Agent recommends follow-up actions

### Financial Analytics
- **Anomaly detection**: Z-score based analysis on revenue, failure rates, refund rates
- **Cash flow forecasting**: 7-30 day predictions with confidence levels and risk assessment
- **Failed transaction analysis**: Failure code clustering and recovery recommendations
- **Refund monitoring**: Rate tracking and root cause identification

### AI Actions & Approval Workflow
- **Action proposals**: Agent creates structured action plans
- **Human-in-the-loop**: Approval required before execution
- **Payment recovery simulation**: Identify retryable failed transactions
- **Audit trail**: Every agent decision, tool call, and action logged

### Security
- **JWT authentication** with configurable expiry
- **Per-merchant data isolation**: Agent only accesses current merchant's data
- **Role-based access control**: merchant_admin role hierarchy
- **Bcrypt password hashing**

---

## Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Frontend** | React | 19.x | UI components |
| | TypeScript | 6.x | Type safety |
| | Vite | 8.x | Build tool & dev server |
| | Tailwind CSS | 4.x | Utility-first styling |
| | Recharts | 3.x | Data visualization |
| | React Router | 7.x | Client-side routing |
| **Backend** | Python | 3.12 | Runtime |
| | FastAPI | 0.115 | Async web framework |
| | SQLAlchemy | 2.0 | ORM (async) |
| | Pydantic | 2.10 | Data validation |
| | Uvicorn | 0.34 | ASGI server |
| **Database** | PostgreSQL | 16 | Primary data store |
| | asyncpg | 0.30 | Async PostgreSQL driver |
| **AI/ML** | OpenAI API | - | LLM provider (GPT-4o) |
| | NumPy | 1.26 | Statistical computations |
| | SciPy | 1.14 | Statistical analysis |
| **Auth** | python-jose | 3.3 | JWT tokens |
| | passlib | 1.7 | Password hashing (bcrypt) |
| **Testing** | pytest | 8.3 | Test framework |
| | pytest-asyncio | 0.24 | Async test support |
| | httpx | 0.28 | Async HTTP client |
| **Infra** | Docker | - | Containerization |
| | Docker Compose | - | Multi-service orchestration |
| | Alembic | 1.14 | Database migrations |

---

## Database Design

```mermaid
erDiagram
    merchants ||--o{ users : "has"
    merchants ||--o{ transactions : "processes"
    merchants ||--o{ refunds : "issues"
    merchants ||--o{ payouts : "receives"
    merchants ||--o{ cash_flow_events : "tracks"
    merchants ||--o{ ai_conversations : "hosts"
    merchants ||--o{ audit_logs : "records"
    merchants ||--o{ ai_actions : "proposes"

    users ||--o{ ai_conversations : "initiates"
    users ||--o{ ai_actions : "approves"

    transactions ||--o{ refunds : "generates"
    transactions ||--o{ payment_failures : "may_fail"

    ai_conversations ||--o{ ai_messages : "contains"
    ai_conversations ||--o{ ai_actions : "triggers"

    merchants {
        uuid id PK
        string name
        string business_name
        string email UK
        string phone
        string business_type
        string currency
        decimal current_balance
        timestamp created_at
    }

    users {
        uuid id PK
        string email UK
        string hashed_password
        string full_name
        string role
        uuid merchant_id FK
        boolean is_active
        timestamp created_at
    }

    transactions {
        uuid id PK
        uuid merchant_id FK
        uuid customer_id FK
        decimal amount
        string currency
        string status
        string payment_method
        string payment_gateway
        string failure_code
        text failure_reason
        timestamp created_at
    }

    refunds {
        uuid id PK
        uuid merchant_id FK
        uuid transaction_id FK
        decimal amount
        string status
        text reason
        timestamp created_at
    }

    cash_flow_events {
        uuid id PK
        uuid merchant_id FK
        string type
        decimal amount
        text description
        string source
        timestamp created_at
    }

    ai_conversations {
        uuid id PK
        uuid merchant_id FK
        uuid user_id FK
        string title
        timestamp created_at
    }

    ai_messages {
        uuid id PK
        uuid conversation_id FK
        string role
        text content
        jsonb tools_called
        jsonb metadata_json
        integer token_count
        timestamp created_at
    }

    ai_actions {
        uuid id PK
        uuid merchant_id FK
        uuid conversation_id FK
        uuid user_id FK
        string action_type
        string action_class
        text description
        jsonb input_data
        jsonb output_data
        decimal estimated_impact
        string risk_level
        string approval_status
        string execution_status
        timestamp created_at
    }

    audit_logs {
        uuid id PK
        uuid merchant_id FK
        uuid user_id
        string action
        string resource_type
        jsonb details
        text user_prompt
        text agent_decision
        jsonb tools_called
        jsonb tool_outputs
        timestamp created_at
    }
```

---

## Security

- **Authentication**: JWT Bearer tokens with configurable expiry (default 24h)
- **Password Storage**: Bcrypt hashing via passlib
- **Data Isolation**: All queries are scoped to `merchant_id` — the agent cannot access cross-merchant data
- **Input Validation**: Pydantic schemas enforce strict field validation on all endpoints
- **CORS**: Configurable allowed origins (default: localhost:5173, localhost:3000)
- **Action Approval**: Financial actions require explicit human approval before execution
- **Audit Logging**: Every AI interaction, tool call, and action is recorded for compliance
- **Global Exception Handler**: Prevents internal error details from leaking to clients

---

## Setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+
- Docker & Docker Compose (optional)
- An OpenAI API key (for AI features)

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://paypilot:paypilot_secret@localhost:5432/paypilot_db` | Async PostgreSQL connection string |
| `DATABASE_URL_SYNC` | Yes | `postgresql://paypilot:paypilot_secret@localhost:5432/paypilot_db` | Sync connection for migrations |
| `JWT_SECRET` | Yes | `change-me-to-a-random-secret-in-production` | Secret key for JWT signing |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `JWT_EXPIRY_MINUTES` | No | `1440` | Token expiry (default 24h) |
| `LLM_API_KEY` | For AI | `""` | OpenAI API key |
| `LLM_MODEL` | No | `gpt-4o` | LLM model identifier |
| `LLM_PROVIDER` | No | `openai` | LLM provider |
| `CORS_ORIGINS` | No | `http://localhost:5173,http://localhost:3000` | Comma-separated allowed origins |
| `APP_ENV` | No | `development` | Environment mode |
| `LOG_LEVEL` | No | `INFO` | Python logging level |

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-org/paypilot-ai.git
cd paypilot-ai

# 2. Copy environment variables
cp .env.example .env
# Edit .env with your values (especially LLM_API_KEY)

# 3. Run with Docker Compose
docker compose up --build

# Or run manually (requires PostgreSQL running separately)
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head  # if migrations exist
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

---

## Running Locally

### Docker Compose (Recommended)

```bash
docker compose up --build
```

This starts:
- **PostgreSQL** on `localhost:5432`
- **Backend** on `localhost:8000`
- **Frontend** on `localhost:5173` (proxies `/api` to backend)

### Manual Setup

**Database**:
```bash
# Ensure PostgreSQL is running, then create the database
createdb paypilot_db
```

**Backend**:
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend**:
```bash
cd frontend
npm install
npm run dev
```

---

## Testing

```bash
cd backend
pip install aiosqlite  # if not already installed
pytest tests/ -v
```

Tests use mocked database sessions and authentication to validate API contract, request/response shapes, and business logic without requiring a running PostgreSQL instance.

**Test coverage**:
- `test_auth.py` — Registration, login, JWT validation, error handling
- `test_analytics.py` — Dashboard summary, revenue trends, payment methods, period comparison
- `test_transactions.py` — Listing, filtering, pagination, failed transactions
- `test_anomaly_detection.py` — Detection endpoint, response schema validation
- `test_forecast.py` — Cash flow forecast, confidence levels
- `test_agent_tools.py` — Tool registration, validation, orchestrator wiring

---

## Demo

### Credentials

| Field | Value |
|-------|-------|
| **Email** | `demo@paypilot.ai` |
| **Password** | `demo123` |

### Scenario Walkthrough

1. **Login** with the demo credentials
2. **Dashboard** — Review today's revenue (₹12,500), success rate (94%), and transaction count (45)
3. **Transactions** — Filter by status to see 3 failed transactions; inspect failure codes
4. **Analytics** — Compare this month vs last month; UPI leads with 96.5% success rate
5. **Anomalies** — View detected anomalies: a revenue drop on Aug 15 and a failure rate spike on Aug 18
6. **Cash Flow** — 7-day forecast shows balance growing to ₹520,000 with 82% confidence
7. **Copilot** — Ask: *"Why did revenue drop last week?"*
   - Agent calls `get_revenue_trend` and `detect_anomalies`
   - Returns evidence-backed analysis with specific figures
8. **Actions** — Review an agent-proposed recovery plan for 5 failed transactions worth ₹7,500
9. **Audit** — See the full trail of agent interactions, tool calls, and decisions

> **Note**: This is a hackathon demonstration project. Payment execution is simulated — no real payments are processed. The Razorpay integration is mocked for demonstration purposes.

---

## Known Limitations

- **Simulated payment execution**: The `simulate_payment_recovery` tool creates action records but does not actually retry payments through Razorpay
- **No real LLM fallback**: If `LLM_API_KEY` is not set, the copilot returns a static message; there is no offline/cheaper model fallback
- **In-memory anomaly detection**: Z-score analysis runs on query results; for very large datasets, this could be optimized with materialized views or pre-computed aggregations
- **No WebSocket support**: Chat interface uses polling; real-time streaming responses would improve UX
- **Single tenant per deployment**: Multi-tenancy is data-isolated via `merchant_id` but not infrastructure-isolated
- **No rate limiting**: API endpoints lack rate limiting, which should be added for production use

---

## Future Improvements

- [ ] **Streaming responses**: Server-Sent Events for real-time agent responses
- [ ] **Scheduled monitoring**: Background tasks for proactive anomaly detection and alerts
- [ ] **Email/Slack notifications**: Push alerts through external channels
- [ ] **Razorpay webhook integration**: Real payment event ingestion for live data
- [ ] **Custom agent personas**: Allow merchants to configure agent behavior and thresholds
- [ ] **Advanced forecasting**: Prophet or ARIMA models for better prediction accuracy
- [ ] **RBAC expansion**: Fine-grained permissions (analyst, viewer, admin roles)
- [ ] **API rate limiting**: Per-merchant rate limits with Redis-backed throttling
- [ ] **E2E test suite**: Playwright tests for the full frontend flow
- [ ] **Observability**: OpenTelemetry tracing and structured logging for production

---

<div align="center">

**Built for the hackathon. Designed for production thinking.**

</div>
