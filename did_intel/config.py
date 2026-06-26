"""
Centralized configuration for DID Intel.

Reads from, in order of precedence:
    1. Environment variables (DIDINTEL_*)
    2. config.json in the project root or user config directory
    3. Hard-coded defaults below
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Defaults (used when nothing else is provided)
# ---------------------------------------------------------------------------
DEFAULTS: Dict[str, Any] = {
    # Cache settings
    "cache_ttl_days": 3,

    # Scraper settings
    "base_url": "https://lookup.robokiller.com",
    "concurrent_requests": 30,
    "timeout": 15,
    "connect_timeout": 5,
    "sock_read_timeout": 10,
    "max_retries": 2,
    "requests_per_second": 5,
    "connection_limit": 100,
    "keepalive_timeout": 30,
    "rotate_user_agents": True,
    "rotate_headers": True,
    "referer_chance": 0.5,

    # API server settings
    "api_host": "0.0.0.0",
    "api_port": 8000,
    "api_reload": False,          # NEVER True in production

    # Security (to be expanded later)
    "api_key_required": False,
    "allowed_api_keys": [],
}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
def _get_project_root() -> Path:
    """Return the directory containing config.json / pyproject.toml."""
    return Path(__file__).resolve().parent.parent


def _get_user_config_dir() -> Path:
    """Return the OS-specific user config directory."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
    return Path(base) / "DIDRepChecker"


def _get_user_cache_dir() -> Path:
    """Return the OS-specific cache directory."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
    else:
        base = Path.home() / ".cache"
    return Path(base) / "DIDRepChecker"


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
def _load_json(path: Path) -> Dict[str, Any]:
    """Safely load a JSON file, returning {} on any failure."""
    try:
        if path.is_file():
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
    except Exception:
        pass
    return {}


def _env_override(key: str, value: Any) -> Any:
    """Check for DIDINTEL_<KEY> env var and override if present."""
    env_key = f"DIDINTEL_{key.upper()}"
    env_val = os.environ.get(env_key)
    if env_val is None:
        return value
    if isinstance(value, bool):
        return env_val.lower() in ("1", "true", "yes", "on")
    if isinstance(value, int):
        return int(env_val)
    if isinstance(value, float):
        return float(env_val)
    if isinstance(value, list):
        return [v.strip() for v in env_val.split(",") if v.strip()]
    return env_val


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def load_config(extra_paths: Optional[list[Path]] = None) -> Dict[str, Any]:
    """
    Build the effective configuration by merging (in order):
      defaults  <  config.json (project)  <  config.json (user dir)  <  env vars
    """
    config = dict(DEFAULTS)

    # 1. Project-level config.json (in repo root)
    project_config = _get_project_root() / "config.json"
    config.update(_load_json(project_config))

    # 2. User-level config.json (persists across installs)
    user_config_dir = _get_user_config_dir()
    user_config = user_config_dir / "config.json"
    config.update(_load_json(user_config))

    # 3. Extra paths passed by caller
    if extra_paths:
        for p in extra_paths:
            config.update(_load_json(p))

    # 4. Environment variable overrides
    for key, value in config.items():
        config[key] = _env_override(key, value)

    return config


# Convenience: load once at import time (can be refreshed by calling load_config again)
_config: Optional[Dict[str, Any]] = None


def get_config() -> Dict[str, Any]:
    """Return the (cached) effective configuration."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config() -> Dict[str, Any]:
    """Force re-read of all config sources."""
    global _config
    _config = load_config()
    return _config


# ---------------------------------------------------------------------------
# Convenience accessors
# ---------------------------------------------------------------------------
PROJECT_ROOT = _get_project_root()
USER_CONFIG_DIR = _get_user_config_dir()
USER_CACHE_DIR = _get_user_cache_dir()
