"""
policy_store.py — persist named verdict policies to config/verdict_policies.json.

Owner: Hessam. Lets a demo user save the rule set they built ("Strict", "Client-A", ...) and
reload it later. Ships with the presets from verdict_engine so the file always has content.
"""

from __future__ import annotations

import json

from src.config import PATHS
from src.verdict_engine import Policy, preset_policies

_STORE = PATHS.config_dir / "verdict_policies.json"


def load_all() -> dict[str, Policy]:
    """Return {name: Policy}. Presets are always included; saved ones override by name."""
    policies = dict(preset_policies())
    if _STORE.exists():
        try:
            raw = json.loads(_STORE.read_text(encoding="utf-8"))
            for name, pdict in raw.items():
                policies[name] = Policy.from_dict(pdict)
        except Exception:
            pass
    return policies


def save(policy: Policy) -> None:
    """Persist (or overwrite) one named policy. Presets are not written unless renamed."""
    existing = {}
    if _STORE.exists():
        try:
            existing = json.loads(_STORE.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    existing[policy.name] = policy.to_dict()
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def delete(name: str) -> None:
    if not _STORE.exists():
        return
    try:
        existing = json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return
    existing.pop(name, None)
    _STORE.write_text(json.dumps(existing, indent=2), encoding="utf-8")
