I'll prepare a comprehensive project summary that you can feed into OpenCode Agent (or any other AI) to continue development. This summary includes the project's purpose, architecture, current state, and specific tasks to work on.

---

## DID Reputation Checker – Project Summary for AI Agents

### 🎯 Project Purpose

The **DID Reputation Checker** is a Windows‑first toolkit that:
- Extracts phone numbers from the Peerless Network web page.
- Scrapes RoboKiller’s public lookup to get reputation data (Positive / Negative, total calls, user reports, last call).
- Provides a FastAPI server with SQLite caching for fast repeated lookups.
- Optionally syncs the local cache to a Google Sheet (two‑way sync, conflict resolution by timestamp).
- Includes a Chrome extension to capture numbers directly from the Peerless page and auto‑select checkboxes.

---

### 🧱 Architecture (Current Stable Version)

We have rolled back to a **simple, fast, Windows‑only** version without the TUI manager. The components are:

| Component | File | Responsibility |
|-----------|------|----------------|
| **FastAPI Server** | `server/api_server.py` | REST API endpoint `/scrape`. Validates numbers, calls scraper, returns JSON. |
| **Scraper Engine** | `server/scraper_engine.py` | Async scraper with rate limiting, retries, and HTML parsing. |
| **Cache** | `server/cache.py` | SQLite storage with TTL (default 3 days). Stores reputation results. |
| **CLI Tool** | `cli_tool/did_cli.py` | Batch processing, interactive mode, CSV/JSON export, clipboard copy. |
| **Google Sheet Sync** | `sync/sync_to_google.py` | Standalone two‑way sync script (runs manually or via scheduler). |
| **Chrome Extension** | `extension/` | Captures DIDs from Peerless page, calls the API, displays results. |
| **Installer (Windows)** | `install_windows.ps1` | Clones repo, creates venv, installs deps, creates `config.json`. |
| **Runner** | `run_windows.bat` | Starts the FastAPI server (production mode, no `--reload`). |

---

### 🗂️ Project Structure (as of rollback)

```
DIDRepChecker/
├── cli_tool/
│   ├── api_client.py
│   └── did_cli.py
├── extension/
│   ├── background.js
│   ├── content.js
│   ├── inject.js
│   ├── manifest.json
│   ├── popup.css
│   ├── popup.html
│   └── popup.js
├── scripts/
│   ├── install_linux.sh
│   ├── install_windows.ps1
│   ├── uninstall_linux.sh
│   └── uninstall_windows.ps1
├── server/
│   ├── __init__.py
│   ├── api_server.py
│   ├── cache.py
│   ├── scraper_engine.py
│   └── requirements.txt
├── sync/
│   ├── sync_to_google.py
│   └── service_account_key.json (optional)
├── config.json
├── requirements.txt
├── run_windows.bat
└── README.md
```

---

### ⚙️ Current Configuration

**`config.json`** (created automatically by installer):

```json
{
    "cache_ttl_days": 3
}
```

**`requirements.txt`** (all dependencies):

```
aiohttp>=3.8.0
lxml>=4.9.0
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
pydantic-settings>=2.0.0
aiosqlite>=0.19.0
rich>=13.0.0
tqdm>=4.65.0
pyperclip>=1.8.0
requests>=2.31.0
```

---

### ✅ What Works

- ✅ FastAPI server starts and responds to `/scrape` requests.
- ✅ SQLite cache with 3‑day TTL (stored in `%LOCALAPPDATA%\DIDRepChecker\` on Windows).
- ✅ Scraper engine with concurrency and rate limiting.
- ✅ Google Sheet sync (manual, via `python sync/sync_to_google.py`).
- ✅ CLI tool for batch processing (`did_cli.py`).
- ✅ Chrome extension (fully functional).
- ✅ Windows installer (`install_windows.ps1`) sets up the environment.

---

### ❌ Known Issues / Broken Parts (after rollback)

1. **`run_windows.bat`** – uses `--reload`, which is for development. Should be removed in production.
2. **`install_windows.ps1`** – sometimes fails to clone repo due to URL typo or network issues; Python path detection can be unreliable.
3. **Cache permissions on Windows** – works, but installer does not explicitly create the cache directory (server creates it on first run).
4. **Sync script** – runs manually; no scheduler or automatic execution.
5. **No request duration logging** – we had it, but it was removed in the rollback. Useful for performance tuning.
6. **CLI tool** – imports `pyperclip` but it was missing from `requirements.txt` (we fixed it).

---

### 🚀 Tasks for Future Development (Priority Order)

1. **Fix Windows installer** – make it robust: verify Python version, handle failed clone, recreate venv if corrupted, create cache directory.
2. **Remove `--reload` from `run_windows.bat`** – or provide separate production/development batch files.
3. **Add request duration logging** to `api_server.py` (middleware and `/scrape` endpoint).
4. **Improve sync script** – add retry logic, batch processing, and configurable interval via `config.json`.
5. **(Optional) Add a lightweight control script** – not a full TUI, but a simple menu to start/stop server and run sync.
6. **Document the Chrome extension** – how to load, configure API URL, and use it.

---

### 🔧 Technical Details for AI Agent

#### Key Functions in `scraper_engine.py`

- `clean_number(number)` → returns 10‑digit string or empty.
- `parse_robokiller_html(html, phone)` → extracts reputation fields.
- `RoboKillerScraper.scrape_async(numbers)` → main async entry point.
- `RoboKillerScraper.scrape(numbers)` → synchronous wrapper for CLI.

#### Database Schema (SQLite)

```sql
CREATE TABLE reputation (
    phone_number      TEXT PRIMARY KEY,
    reputation        TEXT,
    robokiller_status TEXT,
    user_reports      TEXT,
    total_calls       TEXT,
    last_call         TEXT,
    scraped_at        TEXT,
    timestamp         REAL
);
```

#### API Endpoint

- `POST /scrape` – expects JSON `{"numbers": ["2125551234", ...]}`.
- Returns JSON array of objects with fields: `phone_number`, `reputation`, `robokiller_status`, `user_reports`, `total_calls`, `last_call`, `scraped_at`.

#### Sync Script (`sync_to_google.py`)

- Uses `google.oauth2.service_account.Credentials` (modern).
- Reads `config.json` for `cache_ttl_days`.
- Two‑way merge: compares `timestamp` (SQLite) and `last_modified` (sheet).
- Run manually: `python sync/sync_to_google.py`.

---

### 📝 How to Continue

1. **Set up the environment** (already done).
2. **Fix the Windows installer** – this is the most urgent task.
3. **Add request logging** to measure server performance.
4. **Improve sync reliability** (retry, batch).
5. **Optional**: build a lightweight control script (not a heavy TUI).

---

### 🔑 Keys for OpenAI / Anthropic (if needed)

If you are using an AI agent that requires API keys (e.g., OpenCode Agent), you will need to provide:
- **OpenAI API key** (if using GPT‑4 or similar) – set as environment variable `OPENAI_API_KEY`.
- Or **Anthropic key** – set as `ANTHROPIC_API_KEY`.

The agent can then analyse code, write new code, and run tests.

---

### 📦 Recommended Tools (for the AI agent)

- Python 3.9+
- `pip` for dependencies.
- `curl` or `Invoke-WebRequest` for testing API.
- `sqlite3` for inspecting the cache database.
- Google Cloud service account (for sync) – optional.

---

### 🧪 Test Commands

```powershell
# Start the server
cd %LOCALAPPDATA%\DIDRepChecker
.\run_windows.bat

# Test API
curl -X POST http://localhost:8000/scrape -H "Content-Type: application/json" -d "{\"numbers\": [\"2125551234\"]}"

# Run sync manually
python sync\sync_to_google.py
```

---

This summary gives the AI agent a complete picture of the project, its current state, and clear next steps. You can copy this into OpenCode Agent or any other AI tool to continue development seamlessly.