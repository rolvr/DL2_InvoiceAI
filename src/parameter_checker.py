"""
parameter_checker.py — checks OCR'd text for the required reference parameters
(PO Reference, Order Number, Contract Number, Project Reference, Insurance Policy Number,
Bill of Lading Number) plus any user-defined custom fields.

Owner: Damir. Reads its field definitions from config/required_fields_config.json so that
new required fields (or Streamlit-sidebar custom fields) don't require code changes.
"""

import re

from src.config import load_required_fields


def _text_contains_keyword(text: str, keywords: list[str]) -> str | None:
    """Case-insensitive substring search. Returns the matched keyword, or None."""
    lowered = text.lower()
    for kw in keywords:
        if kw.lower() in lowered:
            return kw
    return None


def _text_matches_pattern(text: str, patterns: list[str]) -> str | None:
    """Regex search (case-insensitive). Returns the matched substring, or None."""
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def check_field_presence(text: str, field: dict) -> dict:
    """Check a single field definition against a block of OCR'd text.

    `field` is one entry from required_fields_config.json:
        {"field_name":, "required":, "keywords": [...], "patterns": [...]}

    Returns:
        {"field_name":, "required":, "present": bool, "matched_text": str|None, "match_method": str|None}
    """
    keyword_match = _text_contains_keyword(text, field.get("keywords", []))
    if keyword_match:
        return {
            "field_name": field["field_name"],
            "required": field["required"],
            "present": True,
            "matched_text": keyword_match,
            "match_method": "keyword",
        }

    pattern_match = _text_matches_pattern(text, field.get("patterns", []))
    if pattern_match:
        return {
            "field_name": field["field_name"],
            "required": field["required"],
            "present": True,
            "matched_text": pattern_match,
            "match_method": "pattern",
        }

    return {
        "field_name": field["field_name"],
        "required": field["required"],
        "present": False,
        "matched_text": None,
        "match_method": None,
    }


def check_all_fields(text: str, extra_fields: list[dict] | None = None) -> list[dict]:
    """Check `text` against every field in config/required_fields_config.json's
    default_required_fields + custom_fields, plus any ad-hoc `extra_fields`
    (e.g. a Streamlit-sidebar-entered custom field not yet saved to config)."""
    config = load_required_fields()
    fields = list(config.get("default_required_fields", [])) + list(config.get("custom_fields", []))
    if extra_fields:
        fields = fields + extra_fields

    return [check_field_presence(text, field) for field in fields]


def missing_required_fields(results: list[dict]) -> list[str]:
    """Given check_all_fields() output, return field_names that are required but not present."""
    return [r["field_name"] for r in results if r["required"] and not r["present"]]
