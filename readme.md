Here's the updated `README.md` that includes the new one‑line Windows installer, the current FastAPI server, the Chrome extension, the CLI tool, and all deployment instructions.

```markdown
# DID Reputation Checker

A complete toolkit to extract phone numbers from the Peerless Network page, check their reputation via RoboKiller, and automatically select the desired numbers on the page.

## 📦 What's Inside

- **Chrome Extension** – Captures DIDs from the Peerless API, calls the reputation server, displays sortable/filterable results, and auto‑selects checkboxes.
- **Reputation API Server** – FastAPI‑based REST API that uses an async scraper to look up phone numbers on RoboKiller. Includes SQLite caching, rate limiting, and retries.
- **CLI Tool** – Command‑line interface for batch processing, with real‑time progress, retry logic, clipboard copy, and CSV/JSON export.
- **Deployment Scripts** – One‑command installation for Ubuntu (systemd + Nginx) and one‑line PowerShell installer for Windows.

---

## 🚀 Quick Start (API Server)

### Linux (Ubuntu / Debian)

Run the one‑command installer (as root or with sudo):

```bash
curl -sL https://raw.githubusercontent.com/siamakanda/DIDRepChecker/main/scripts/bootstrap.sh | sudo bash
```

This will:
- Install system dependencies (Python, Nginx, Git).
- Clone the repository to `/opt/did-reputation-api`.
- Set up a Python virtual environment and install dependencies.
- Create a systemd service (`did-api`) running Gunicorn with Uvicorn workers.
- Configure Nginx as a reverse proxy on port 80.
- Start the service.

After installation, the API is available at `http://<server-ip>/scrape`.

### Windows (One‑line PowerShell Installer)

Open **PowerShell as Administrator** and run:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/siamakanda/DIDRepChecker/main/scripts/install_windows.ps1'))
```

This will:
- Install Git and Python if missing.
- Clone the repository to `C:\Program Files\DIDReputationAPI`.
- Create a virtual environment and install Python dependencies.
- **Does not** start the server automatically – run `run_windows.bat` from the installation folder to start manually.

To start the server manually:

```cmd
cd C:\Program Files\DIDReputationAPI
run_windows.bat
```

The API will be available at `http://localhost:8000/scrape`.

### Manual Run (Any OS)

```bash
cd server
pip install -r requirements.txt
uvicorn api_server:app --reload
```

---

## 🧩 Chrome Extension

### Installation (Developer Mode)

1. Clone the repository.
2. Open Chrome and go to `chrome://extensions/`.
3. Enable **Developer mode** (top right).
4. Click **Load unpacked** and select the `extension` folder.
5. The extension icon will appear in the toolbar.

### Usage

1. Navigate to the **Peerless Network number selection page** (`https://animate.peerlessnetwork.com/...`).
2. Click the extension icon.
3. **Numbers tab** – The extension automatically captures all DIDs from the page (via API sniffing). You can also paste your own numbers.
4. **Send to API** – Select numbers (or use “Top N from page”) and click “Check Reputation”. The server will return reputation data.
5. **Results tab** – View results in a sortable/filterable table (default filter: Positive). Copy DIDs, export CSV, or retry errors.
6. **Select on Page** – Choose “Top N from results” or “Select Checked” to automatically tick the corresponding checkboxes on the Peerless page (including newly loaded rows).

### Features

- **Auto‑capture** via API sniffing (no need to manually extract numbers).
- **Paste numbers** manually as an alternative.
- **Dark mode** toggle (persistent).
- **Persistent preferences** (filter, sort, N values).
- **Row selection** in results table.
- **Auto‑switch to Results tab** when reputation data arrives.
- **Selection count message** after selecting on the page.

---

## 🖥️ CLI Tool

The CLI tool (`cli_tool/did_cli.py`) processes phone numbers directly from the terminal.

### Usage

```bash
# Activate virtual environment (from the server directory)
cd server
source venv/bin/activate   # or venv\Scripts\activate on Windows

# Run the CLI
python ../cli_tool/did_cli.py -f numbers.txt --filter positive --sort total_calls --order asc --limit 70
```

### Options

| Flag | Description |
|------|-------------|
| `-f FILE` | Read numbers from a file (one per line or CSV first column) |
| `-n "NUMBERS"` | Provide numbers directly (comma or space separated) |
| `--once` | Run once and exit (default is continuous loop) |
| `--no-interactive` | Skip interactive prompts (use flags for filter/sort/limit) |
| `--filter {positive,negative,all}` | Filter results by reputation |
| `--sort {total_calls,user_reports,last_call,phone_number}` | Sort field |
| `--order {asc,desc}` | Sort order |
| `--limit N` | Maximum number of results |
| `--export FILE` | Export full results to CSV or JSON |

### Examples

```bash
# Interactive paste mode (loop by default)
python did_cli.py

# Process a file once, output top 70 positive numbers by fewest calls
python did_cli.py -f numbers.txt --once --filter positive --sort total_calls --order asc --limit 70

# Non‑interactive, export full results to CSV
python did_cli.py -f numbers.csv --no-interactive --export results.csv
```

---

## 📁 Project Structure

```
DIDRepChecker/
├── extension/              # Chrome extension source
│   ├── manifest.json
│   ├── background.js
│   ├── content.js
│   ├── inject.js
│   ├── popup.html
│   ├── popup.css
│   └── popup.js
├── server/                 # FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── scraper_engine.py
│   │   ├── cache.py
│   │   ├── models.py
│   │   └── config.py
│   ├── requirements.txt
│   ├── installer_windows.bat
│   └── run_windows.bat
├── cli_tool/               # Command‑line interface
│   └── did_cli.py
├── scripts/                # Deployment automation
│   ├── bootstrap.sh
│   ├── deploy_linux.sh
│   ├── install_windows.ps1
│   └── uninstall.sh
├── requirements.txt        # Root dependencies (if any)
└── README.md
```

---

## 🛠️ Requirements

- Python 3.9+
- Chrome browser (for the extension)
- Dependencies are listed in `server/requirements.txt` and `cli_tool/requirements.txt` (if separated).

For the server deployment on Linux, you also need `nginx`, `systemd`, and `git`.

---

## 🤝 Contributing

Feel free to open issues or pull requests on [GitHub](https://github.com/siamakanda/DIDRepChecker). For major changes, please discuss them first.

---

## 📄 License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- [RoboKiller Lookup](https://lookup.robokiller.com) – Reputation data source.
- [Peerless Network](https://animate.peerlessnetwork.com) – DID inventory page.
- All the open‑source libraries used.

---

**Enjoy automated DID reputation checking!** 🚀
```

This README now includes:
- The one‑line PowerShell installer for Windows (with a note that the server does not start automatically – user must run `run_windows.bat`).
- Updated folder structure reflecting the `scripts/install_windows.ps1`.
- All current features of the extension (auto‑switch to Results, default Positive filter, selection count message, etc.).
- Consistent command examples for CLI, extension, and server.

You can replace your existing `README.md` with this content.