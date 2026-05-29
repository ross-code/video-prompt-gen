"""Simple JSON-file persistence for the user's profile and last results.

Keeps the most recent search around so the page shows something on reload without
re-spending an API call. The location can be overridden with CONF_FINDER_DATA.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def _data_dir() -> Path:
    override = os.environ.get("CONF_FINDER_DATA")
    base = Path(override) if override else Path.home() / ".conference-finder"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _state_file() -> Path:
    return _data_dir() / "state.json"


def load_state() -> dict:
    """Return the saved state, or sensible empty defaults."""
    path = _state_file()
    if not path.exists():
        return {"profile": {}, "conferences": [], "last_updated": None}
    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {"profile": {}, "conferences": [], "last_updated": None}
    data.setdefault("profile", {})
    data.setdefault("conferences", [])
    data.setdefault("last_updated", None)
    return data


def save_state(profile: dict, conferences: list[dict]) -> str:
    """Persist the profile and conferences; returns the ISO update timestamp."""
    last_updated = datetime.now(timezone.utc).isoformat()
    payload = {
        "profile": profile,
        "conferences": conferences,
        "last_updated": last_updated,
    }
    tmp = _state_file().with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    tmp.replace(_state_file())
    return last_updated
