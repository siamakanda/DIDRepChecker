# DIDRepChecker

Chrome extension + local API to check phone number reputations via RoboKiller and auto-select DIDs on the Peerless Animate portal.

## What's Inside

- **Chrome Extension** — Captures DIDs from the Peerless API, checks reputation via the local server, displays sortable/filterable results, and auto-selects checkboxes on the page.
- **API Server** — FastAPI backend with async RoboKiller scraper, SQLite cache, rate limiting.
- **CLI Tool** — Batch processing, interactive mode, CSV/JSON export, clipboard copy.
- **Deployment Scripts** — One-command install for Windows.

## Quick Start

### Install

Run this from the project root:

```
powershell -ExecutionPolicy Bypass -File deploy\windows\install.ps1
```

This creates a `venv/` in the project root, installs all dependencies, and installs the package.

### Start the Server

```
deploy\windows\run.bat
```

Or from PowerShell:

```
venv\Scripts\activate
python -m uvicorn did_intel.api:app --host 127.0.0.1 --port 8000
```

The API is at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

### Load the Extension

1. Open Chrome → `chrome://extensions/`
2. Enable **Developer mode**
3. Click **Load unpacked** → select the `extension/` folder

### Usage

1. Navigate to `https://animate.peerlessnetwork.com/...`
2. Click the extension icon
3. Numbers auto-capture when the portal loads
4. Click **Check Reputation** → results appear in the Results tab
5. Click **Select on Page** to tick checkboxes on the portal

## API

**POST `/scrape`** — Send up to 500 phone numbers, get reputation data back.

```json
{"numbers": ["2125551234", "2125555678"]}
```

**GET `/health`** — Health check.

## Configuration

`config.json` in the project root (optional — defaults are fine):

```json
{
    "cache_ttl_days": 3,
    "concurrent_requests": 30,
    "requests_per_second": 5,
    "api_host": "127.0.0.1",
    "api_port": 8000
}
```

Environment variables with `DIDRCK_` prefix override all settings (e.g. `DIDRCK_API_PORT=9000`).

## CLI

```bash
# Interactive mode
didrepchecker

# Batch mode from file
didrepchecker -f numbers.txt --once --filter positive --sort total_calls --order asc --limit 70

# Cache stats
didrepchecker --stats
```

## Uninstall

```
powershell -ExecutionPolicy Bypass -File deploy\windows\uninstall.ps1
```

Removes `venv/` and build artifacts. Source files stay.

## Structure

```
DIDRepChecker/
├── extension/           # Chrome extension
├── src/did_intel/       # Python package
│   ├── api.py           # FastAPI server
│   ├── scraper.py       # RoboKiller scraper engine
│   ├── cache.py         # SQLite cache
│   ├── cli.py           # CLI tool
│   ├── client.py        # API client
│   ├── config.py        # Config management
│   └── utils.py         # Shared utilities
├── deploy/windows/      # Install/uninstall scripts
├── tests/               # Test suite
├── pyproject.toml
└── config.example.json
```

## License

MIT
