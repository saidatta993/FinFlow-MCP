# 💸 FinFlow — AI-Powered Personal Finance Dashboard

> **Talk to your money.** Ask questions in plain English, get live charts on a real-time dashboard.

---

## What It Does

FinFlow automatically ingests transaction alerts from your HDFC Bank email, parses them, and stores them in a local SQLite database.
You interact with your finances through **Claude Desktop** — ask natural-language questions like _"Where did I overspend this month?"_ and Claude queries your data via MCP tools.
The answers are rendered as **live, interactive charts** (bar, pie, line) on a React dashboard streamed in real-time over Server-Sent Events (SSE).

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Claude Desktop                            │
│                     (MCP Host / LLM Client)                      │
└──────┬──────────────────────────────────┬────────────────────────┘
       │ stdio (MCP)                      │ stdio (MCP)
       ▼                                  ▼
┌──────────────┐                  ┌───────────────┐
│  data-server │                  │   ui-server   │
│  (MCP Server)│                  │  (MCP Server) │
│              │                  │  + FastAPI SSE │
│  Tools:      │                  │               │
│  • get_recent│                  │  Tool:        │
│    _expenses │                  │  • update_    │
│  • get_categ │  ┌────────────┐  │    dashboard  │
│    ory_summ. │  │ finance.db │  │    _chart     │
│  • execute_  ├──┤  (SQLite)  ├──┤               │
│    query     │  └────────────┘  │  REST:        │
│  • get_spend │                  │  GET /sessions│
│    ing_anom. │                  │  DEL /sessions│
└──────────────┘                  └───────┬───────┘
                                          │ SSE stream
       ┌──────────────────┐               │ :8000/sse/dashboard
       │  Gmail API       │               ▼
       │  (HDFC alerts)   │      ┌─────────────────┐
       └────────┬─────────┘      │    frontend      │
                │                │  (React + Vite)  │
                ▼                │  Recharts, TW    │
       ┌──────────────┐         │  Live dashboard  │
       │  ingest.py   │         └─────────────────-┘
       │  parser.py   │              :5173
       │  gmail_client│
       └──────────────┘
```

**Data flow:**
1. `ingest.py` pulls HDFC debit alert emails via Gmail API → `parser.py` extracts amount/merchant/date → stored in `finance.db`
2. User asks Claude a question → Claude calls **data-server** MCP tools to query the DB
3. Claude formats the answer and calls **ui-server** `update_dashboard_chart` tool
4. ui-server broadcasts the chart payload via SSE → React frontend renders it live

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **LLM Host** | Claude Desktop (MCP client) |
| **Backend — Data** | Python, MCP SDK, SQLite |
| **Backend — UI Bridge** | Python, FastAPI, SSE-Starlette, Uvicorn |
| **Frontend** | React 19, TypeScript, Vite, Recharts, Tailwind CSS |
| **Email Ingestion** | Gmail API (OAuth 2.0) |
| **Database** | SQLite (`finance.db`) |

---

## 📂 Project Structure

```
FinFlow_MCP_v2/
├── data-server/              # MCP server — financial data tools
│   ├── main.py               # MCP tool definitions & handlers
│   ├── db.py                 # SQLite helpers (expenses, sessions, anomalies)
│   ├── gmail_client.py       # Gmail API OAuth + email fetching
│   ├── parser.py             # Regex parser for HDFC bank alerts
│   ├── ingest.py             # Orchestrates email → DB pipeline
│   ├── categories.csv        # Merchant → category keyword mapping
│   ├── requirements.txt
│   └── .env
│
├── ui-server/                # MCP server — dashboard bridge + SSE
│   ├── main.py               # MCP tool + FastAPI SSE + session REST
│   ├── sse_manager.py        # Thread-safe SSE broadcast manager
│   ├── requirements.txt
│   └── .env
│
├── frontend/                 # React dashboard (Vite + TypeScript)
│   ├── src/
│   │   ├── App.tsx           # Main dashboard layout
│   │   ├── components/
│   │   │   └── ChartRenderer.tsx  # Bar / Pie / Line chart component
│   │   └── hooks/
│   │       ├── useSSE.ts     # SSE connection hook
│   │       └── useSessions.ts # Session history hook
│   ├── index.html
│   └── package.json
│
└── README.md                 # ← You are here
```

---

## 🚀 Local Setup

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** and **npm**
- **Claude Desktop** installed with MCP support
- A **Google Cloud project** with Gmail API enabled and OAuth credentials (`credentials.json`)

### 1. Clone & create a virtual environment

```bash
git clone <your-repo-url>
cd FinFlow_MCP_v2

python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 2. Install Python dependencies

```bash
pip install -r data-server/requirements.txt
pip install -r ui-server/requirements.txt
```

### 3. Configure environment variables

**`data-server/.env`**
```env
GMAIL_CREDENTIALS_JSON=./credentials.json
GMAIL_TOKEN_JSON=./token.json
DB_PATH=./finance.db
CATEGORIES_CSV=./categories.csv
```

**`ui-server/.env`**
```env
SSE_PORT=8000
SSE_HOST=0.0.0.0
```

### 4. Set up Gmail OAuth (first-time only)

1. Place your `credentials.json` (from Google Cloud Console) in `data-server/`
2. Run the ingestion script — it will open a browser for OAuth consent:
   ```bash
   cd data-server
   python ingest.py
   ```
3. A `token.json` will be created automatically after authorization.

### 5. Install & run the frontend

```bash
cd frontend
npm install
npm run dev
```
The dashboard will be available at **http://localhost:5173**

### 6. Register MCP servers in Claude Desktop

Add the following to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "finflow-data": {
      "command": "python",
      "args": ["<full-path-to>/data-server/main.py"]
    },
    "finflow-ui": {
      "command": "python",
      "args": ["<full-path-to>/ui-server/main.py"]
    }
  }
}
```

> Replace `<full-path-to>` with the absolute path to your `FinFlow_MCP_v2` directory.

### 7. Start using it!

1. Open **Claude Desktop** — both MCP servers will connect automatically
2. Open **http://localhost:5173** in your browser
3. Ask Claude something like:
   - _"Show me my spending by category for June 2025"_
   - _"What are my top 5 merchants this month?"_
   - _"Are there any spending anomalies in May?"_

---

## 🔧 MCP Tools Reference

### data-server (`finflow-data`)

| Tool | Description |
|------|-------------|
| `get_recent_expenses` | Returns raw expense rows, optionally filtered by month |
| `get_category_summary` | Aggregated spend by category for a given month |
| `execute_query` | Run arbitrary read-only SQL against the expenses table |
| `get_spending_anomalies` | Flags merchants where monthly spend is >50% above the 3-month average |

### ui-server (`finflow-ui`)

| Tool | Description |
|------|-------------|
| `update_dashboard_chart` | Pushes a chart (bar/pie/line) + AI summary to the live dashboard via SSE |

---

## 🎬 Demo Video

📹 **[Watch the demo →](https://your-demo-video-link-here)**

> _Replace the link above with your actual demo video URL (YouTube, Loom, Google Drive, etc.)._

---

## 📄 License

This project is for personal/educational use.
