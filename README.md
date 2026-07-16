# Multi-Agent Emergency Resource Negotiation Platform
### Live Command Center for Real-Time Triage Allocation & explainability

A production-grade, multi-agent platform designed for hospital operations during mass emergency incidents. The system resolves overlapping resource bottlenecks (ICU beds, doctors, operating rooms, ventilators, and staff) using a **deterministic multi-criteria Contract Net Protocol (CNP)** negotiation loop, with dynamic LLM explainability integrations (BYOK).

---

## 🏛️ System Architecture

```
           +---------------------------------------------------------+
           |               React Command Center Dashboard            |
           |   (Triage Ingest, Floor Heatmap, Live SVGs, Settings)   |
           +--------------------+-------------------+----------------+
                                |                   ^
                                | HTTP REST         | WebSockets Live
                                v                   |
           +--------------------+-------------------+----------------+
           |                    FastAPI Backend Gate                 |
           +-----------------------------+---------------------------+
                                         |
                       +-----------------+-----------------+
                       |                                   |
                       v                                   v
        +--------------+--------------+     +--------------+--------------+
        |  Deterministic CNP Engine   |     |    BYOK AI Decision Log     |
        |  (NetworkX Dependency Graph) |     |  (Dynamic LLMClient Adapter)|
        +--------------+--------------+     +--------------+--------------+
                       |                                   |
                       +-----------------+-----------------+
                                         |
                                         v
                      +------------------+------------------+
                      |         SQLite / PostgreSQL         |
                      |   (Secure AES Key Encryption)       |
                      |   (SHA-256 Cryptographic Audit Chain|
                      +-------------------------------------+
```

---

## 🤖 AI Bring Your Own Key (BYOK) Integration

> [!IMPORTANT]
> **AI Operations boundary & Determinism Statement:**
> 1. The core resource allocation engine is **completely deterministic** and runs independently of LLM availability. It uses mathematical weighting and NetworkX DAG cascade impact checks.
> 2. AI is strictly decoupled and used exclusively for **decision narrative explanation**, **clinical operations synthesis**, and **incident executive summaries**.
> 3. If no API key is configured, AI features degrade gracefully, showing a fallback notice, while the EOC queue negotiation continues working at 100% capacity.

### Supported Providers & Models
*   **Google Gemini:** `gemini-1.5-flash`, `gemini-2.5-flash`
*   **OpenAI:** `gpt-4o-mini`, `gpt-4o`
*   **Anthropic Claude:** `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022`

### BYOK Setup Instructions
1. Log in to the application and navigate to the **AI Config (BYOK)** tab.
2. Select your provider, model name, and paste your API key.
3. Adjust model temperature and max tokens.
4. Click **Verify Connection** to execute a live, secure test connection handshake before saving.
5. Click **Save Configuration** to store parameters. The API key is encrypted using AES-256 (Fernet) at rest.

---

## 🔒 Cybersecurity Matrix

*   **Audit Chain Immutability:** Allocations and audit logs are cryptographically linked in a blockchain format where:
    $$\text{Checksum}_n = \text{SHA-256}(\text{RecordData}_n + \text{Checksum}_{n-1})$$
    A dedicated `/api/analytics/validate-chain` route dynamically scans and flags any out-of-order manipulation.
*   **Role-Based Access Control (RBAC):** Endpoints require JWT validation. Clearance mapping:
    *   *Administrator:* Access to AI configurations, logs, and override options.
    *   *Emergency Coordinator:* Access to ingest cases, trigger simulations, and override resources.
    *   *Doctor/Nurse/Manager/Observer:* Read-only command center view.
*   **Data Security:** Stored API keys are encrypted at rest using a machine-local Fernet token generated dynamically at first boot. No keys are hardcoded or stored in Git.

---

## 🚀 Execution & Deployment

### Local Development Setup

#### 1. Backend Service
```bash
cd backend
pip install -r requirements.txt
python -m app.db.seed
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
*   API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
*   Seed logins (Password is `<username>_user`):
    *   Admin: `admin` (pwd: `admin_user`)
    *   Coordinator: `coord` (pwd: `coordinator_user`)
    *   Clinical Staff: `doctor` (pwd: `doctor_user`), `nurse` (pwd: `nurse_user`)

#### 2. Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```
*   App URL: [http://localhost:3000](http://localhost:3000)

### Production Docker Deployment
```bash
docker-compose up --build -d
```
*   Maps frontend to port `3000` and API to `8000`.
*   Includes automatic health checks and database state persistence.

---

## 🧪 Testing Suite
Execute the automated validation suite verifying agent bidding, dependency DAGs, encryption, and API endpoints:
```bash
cd backend
pytest -v
```
