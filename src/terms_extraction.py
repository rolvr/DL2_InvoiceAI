"""
terms_extraction.py — extract payment terms, due dates, and terms & conditions signals
from OCR'd text.

Owner: Damir. Keeps regex/keyword logic centralized so both the notebook and the Streamlit
app produce identical results.
"""

import re

# Common payment-terms phrasings ("Net 30", "due within 15 days", ...)
_PAYMENT_TERMS_PATTERNS = [
    r"net\s?\d{1,3}",
    r"due\s+(?:within|in)\s+\d{1,3}\s+days?",
    r"payment\s+due\s+(?:within|in)?\s*\d{1,3}\s*days?",
    r"\d{1,3}\s*[- ]day(?:s)?\s+(?:payment\s+)?terms?",
]

# Date patterns: 2026-07-21, 07/21/2026, 21-07-2026, "July 21, 2026", "21 July 2026"
_DATE_PATTERNS = [
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    r"\b\d{1,2}-\d{1,2}-\d{2,4}\b",
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}\b",
    r"\b\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?),?\s+\d{4}\b",
]

_CLAUSE_KEYWORDS = {
    "late_payment_clause_detected": ["late payment", "overdue", "past due", "interest will accrue", "late fee"],
    "dispute_clause_detected": ["dispute", "disputed invoice", "arbitration", "governing law"],
    "penalty_clause_detected": ["penalty", "penalties", "liquidated damages", "fine of"],
}


def extract_payment_terms(text: str) -> str | None:
    """Return the first payment-terms phrase found (e.g. 'Net 30'), or None."""
    for pattern in _PAYMENT_TERMS_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def extract_dates(text: str) -> list[str]:
    """Return all date-like substrings found in text, in order of appearance."""
    dates = []
    for pattern in _DATE_PATTERNS:
        dates.extend(re.findall(pattern, text, flags=re.IGNORECASE))
    return dates


def extract_billing_due_days(text: str) -> int | None:
    """Pull the numeric day count out of a 'Net 30' / 'due within 30 days' style phrase."""
    match = re.search(r"(?:net\s?|due\s+(?:within|in)\s+)(\d{1,3})", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def detect_clauses(text: str) -> dict:
    """Flag late-payment / dispute / penalty language in a terms & conditions block."""
    lowered = text.lower()
    return {
        flag_name: any(kw in lowered for kw in keywords)
        for flag_name, keywords in _CLAUSE_KEYWORDS.items()
    }


def summarize_terms(text: str, max_chars: int = 240) -> str:
    """Very light extractive 'summary' — first sentence(s) up to max_chars. Good enough for
    a demo; swap in an LLM call here later if desired, but keep this rule-based fallback so
    the pipeline has no hard external-API dependency."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_period = truncated.rfind(".")
    return truncated[: last_period + 1] if last_period > 40 else truncated + "..."


def extract_terms_and_conditions(region_texts: dict) -> dict:
    """Build the full 'payment_context' + 'terms_and_conditions' block for the final JSON,
    given a dict of {region_label: ocr_text} from Damir's OCR step.

    Expected keys in region_texts (any may be missing/empty): 'due_date_region',
    'date_region', 'payment_terms_region', 'terms_and_conditions_region'.
    """
    payment_terms_text = region_texts.get("payment_terms_region", "") or ""
    terms_text = region_texts.get("terms_and_conditions_region", "") or ""
    date_text = region_texts.get("date_region", "") or ""
    due_date_text = region_texts.get("due_date_region", "") or ""

    invoice_dates = extract_dates(date_text)
    due_dates = extract_dates(due_date_text) or extract_dates(payment_terms_text)

    payment_context = {
        "invoice_date": invoice_dates[0] if invoice_dates else None,
        "due_date": due_dates[0] if due_dates else None,
        "payment_terms": extract_payment_terms(payment_terms_text) or extract_payment_terms(terms_text),
        "billing_due_days": extract_billing_due_days(payment_terms_text) or extract_billing_due_days(terms_text),
    }

    clauses = detect_clauses(terms_text)
    terms_and_conditions = {
        "region_detected": bool(terms_text.strip()),
        **clauses,
        "extracted_text": terms_text,
        "summary": summarize_terms(terms_text) if terms_text.strip() else "",
    }

    return {"payment_context": payment_context, "terms_and_conditions": terms_and_conditions}
