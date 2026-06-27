# Changelog

## 2.2.0 — 2026-06-27

### Added
- Structured JSON error responses (`{"error": "...", "detail": "..."}`) for all endpoints
- Max 500 numbers per `/scrape` request with clear error message
- In-memory rate limiter (30 req/s per IP, 60 burst) — `/health` and `/metrics` exempt
- Extension auto-fallback: if API sniffer fails, triggers scroll-based DID extraction after 5s
- App header with branding in extension popup
- Tab badge (red dot) on Results tab when new data arrives
- Results summary cards (Positive / Negative / Other counts)
- Column header click to sort in results table
- Click-to-copy DID cells with visual feedback
- Row-wide click to select checkboxes
- Cancel scrape button in progress overlay
- "Test Connection" button in Settings with health check
- URL validation with green/red visual feedback
- Onboarding 3-step guide for first-time users
- Scraped-data age indicator ("5m ago")
- Live progress count ("45 / 200 DIDs") in overlay
- Keyboard navigation (arrow keys, space) in results table
- Prometheus `/metrics` endpoint
- Docker support (`Dockerfile`, `.dockerignore`)
- GitHub Actions CI (test on Python 3.10–3.13 + manifest validation)
- Pre-commit hooks (pytest + manifest validate)
- CLI `didintel --stats` flag for cache diagnostics

### Changed
- Reorganized to `src/did_intel/` package structure
- Extension manifest port 5000 → 8000
- Unified `clean_number` in `did_intel.utils`
- CORS restricted from `*` to extension + localhost origins
- `verify_api_key` uses cached config (no disk I/O per request)
- `_legacy_scraper` lazy-initialized instead of module-level
- Extension scroll fallback optimized (45s → 6s max)
- Linux nginx rate limit 30/min → 300/min
- `run.bat` reads host/port from config.json, uses `didintel-server`
- All `var` → `const`/`let` in popup.js
- Google Fonts removed from extension CSS (works offline)
- Extension results no longer cleared before API fetch completes

### Removed
- `prompt.txt`, `project_summery.md`, stale `did_intel/` at root
- `sortSelect` dropdown (replaced by column header sort)

---

## 2.0.0 — 2026-06

### Added
- Initial release
- Chrome extension with API sniffer, reputation checks, checkbox auto-select
- FastAPI server with async scraper engine
- SQLite cache with TTL
- CLI tool for batch processing
- Windows and Linux deployment scripts
