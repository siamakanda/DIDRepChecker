# DID Reputation Checker

A complete toolkit to extract phone numbers from the Peerless Network page, check their reputation via RoboKiller, and automatically select the desired numbers on the page.

## 📦 What's Inside

- **Chrome Extension** – Captures DIDs from the Peerless API, calls the reputation server, displays sortable/filterable results, and auto‑selects checkboxes.
- **Reputation API Server** – Flask‑based REST API that uses the `scraper_engine` to look up phone numbers on RoboKiller.
- **CLI Tool** – Command‑line interface for batch processing, with real‑time progress, retry logic, and CSV/JSON export.

---

## 🚀 Deploy the Reputation API Server

The API server can be deployed on any Ubuntu/Debian system (local LAN or cloud). Use the **automated deployment script** for a one‑command setup.

### Prerequisites

- Ubuntu 20.04 / 22.04 (or any Debian‑based distribution)
- `sudo` access
- Internet connection to clone the repository and install packages

### One‑Command Deployment

Run this on your server (or VM):

```bash
curl -sL https://raw.githubusercontent.com/siamakanda/DIDRepChecker/main/bootstrap.sh | sudo bash