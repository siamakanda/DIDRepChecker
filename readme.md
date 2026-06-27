```markdown
# DID Reputation Checker

A complete toolkit to extract phone numbers from the Peerless Network page, check their reputation via RoboKiller, and automatically select the desired numbers on the page.

## 📦 What's Inside

- **Chrome Extension** – Captures DIDs from the Peerless API, calls the reputation server, displays sortable/filterable results, and auto‑selects checkboxes.
- **Python Package (`src/did_intel`)** – FastAPI server, async RoboKiller scraper, SQLite cache, and CLI tool in one package.
- **Deployment Scripts** – One‑command installation for Ubuntu (systemd + Nginx) and one‑line PowerShell installer for Windows.

---

## 🚀 Quick Start (API Server)

### Linux (Ubuntu / Debian)

Run the one‑command installer (as root or with sudo):

```bash
curl -sL https://raw.githubusercontent.com/siamakanda/DIDRepChecker/main/scripts/install_linux.sh | sudo bash
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
- Clone the repository into the **current working directory**.
- Create a virtual environment and install Python dependencies.
- **Does not** start the server automatically – run `run_windows.bat` from the installation folder to start manually.

To start the server manually:

```cmd
cd <where-you-ran-the-installer>
run_windows.bat
```

The API will be available at `http://localhost:8000/scrape`.

### Manual Run (Any OS)

```bash
cd src
pip install -e .
cd ..
uvicorn did_intel.api:app --reload
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

The CLI tool (`src/did_intel/cli.py`) processes phone numbers directly from the terminal.

### Usage

```bash
# Activate virtual environment
source venv/bin/activate   # or venv\Scripts\activate on Windows

# Install the package (first time only)
pip install -e .

# Run the CLI
didintel -f numbers.txt --filter positive --sort total_calls --order asc --limit 70
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
didintel

# Process a file once, output top 70 positive numbers by fewest calls
didintel -f numbers.txt --once --filter positive --sort total_calls --order asc --limit 70

# Non‑interactive, export full results to CSV
didintel -f numbers.csv --no-interactive --export results.csv
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
├── src/                    # Python package
│   ├── pyproject.toml
│   └── did_intel/
│       ├── __init__.py
│       ├── api.py          # FastAPI server
│       ├── scraper.py      # RoboKiller scraper engine
│       ├── cache.py        # SQLite cache
│       ├── cli.py          # Interactive CLI tool
│       ├── client.py       # API client
│       └── config.py       # Configuration management
├── deploy/
│   ├── windows/            # Windows installer, runner, uninstaller
│   │   ├── install.ps1
│   │   ├── run.bat
│   │   └── uninstall.ps1
│   └── linux/              # Linux installer, systemd, nginx
│       ├── install.sh
│       ├── uninstall.sh
│       ├── did-intel.service
│       └── nginx.conf
├── requirements.txt
├── config.example.json
├── LICENSE
└── README.md
```

---

## 🛠️ Requirements

- Python 3.9+
- Chrome browser (for the extension)
- Dependencies are listed in `requirements.txt`.

For server deployment on Linux, you also need `nginx`, `systemd`, and `git`.

---

## 🐳 Docker

```bash
docker build -t did-intel .
docker run -p 8000:8000 did-intel
```

Configure via environment variables:
```bash
docker run -p 8000:8000 -e DIDINTEL_API_KEY_REQUIRED=true -e DIDINTEL_ALLOWED_API_KEYS=mykey did-intel
```

---

## 🧪 Testing

```bash
pip install -r requirements.txt
pip install -e .
pytest tests -v
```

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