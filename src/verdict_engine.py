"""
verdict_engine.py — user-configurable "obligation-readiness" verdict.

Owner: Hessam (integration). The demo app lets a user BUILD a policy (a set of enabled rules)
and then judges each invoice against it, rather than applying one hardcoded rule. This module
is the rule engine behind that; it is pure logic (no Streamlit, no I/O) so it is unit-testable
and reused identically by the single-invoice and whole-batch paths.

Design (decided with the product owner):
  * Rule types: visual mark, reference-number presence, invoice-date range, payment-terms days.
  * Each rule can be enabled/disabled. The verdict is the AND of every ENABLED rule.
  * FAIL-CLOSED: if an enabled rule has no signal for an invoice (e.g. that invoice was never
    OCR'd), the rule is `unknown`, which counts as a FAIL — a readiness gate must not pass what
    it cannot confirm. The breakdown surfaces this as "unknown — treated as fail", never silently.

This sits ON TOP of the fixed final-JSON schema; it does not change `final_json_builder`'s
`pistacio_readiness` block (which the interface contract still requires).

Signals dict shape (see `src.streamlit_helpers.derive_invoice_signals`), every key optional:
    {
      "stamp_detected": bool | None,
      "signature_detected": bool | None,
      "references": {"PO Reference": bool, "Contract Number": bool, "Work Order No.": bool, ...}
                    | None,          # None => unknown (no OCR); {} => OCR ran, nothing found
      "invoice_date": "YYYY-MM-DD" | None,
      "billing_due_days": int | None,
    }
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Rule status
# ---------------------------------------------------------------------------
PASS = "pass"
FAIL = "fail"
UNKNOWN = "unknown"  # no signal -> treated as fail (fail-closed), but reported distinctly

Status = Literal["pass", "fail", "unknown"]


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------
@dataclass
class VisualRule:
    """Require a stamp and/or signature.

    mode:
      'either' -> stamp OR signature   (default)
      'both'   -> stamp AND signature
      'stamp'  -> stamp only
      'signature' -> signature only
    """

    enabled: bool = True
    mode: Literal["either", "both", "stamp", "signature"] = "either"
    kind: Literal["visual"] = "visual"
    name: str = "Visual mark"

    def evaluate(self, signals: dict) -> "RuleResult":
        s = signals.get("stamp_detected")
        g = signals.get("signature_detected")
        if s is None and g is None:
            return RuleResult(self.name, self.enabled, UNKNOWN,
                              "no stamp/signature prediction for this invoice")
        s, g = bool(s), bool(g)
        if self.mode == "stamp":
            ok, found = s, f"stamp={s}"
        elif self.mode == "signature":
            ok, found = g, f"signature={g}"
        elif self.mode == "both":
            ok, found = s and g, f"stamp={s}, signature={g}"
        else:  # either
            ok, found = s or g, f"stamp={s}, signature={g}"
        return RuleResult(self.name, self.enabled, PASS if ok else FAIL,
                          f"require {self.mode}; {found}")


@dataclass
class ReferenceRule:
    """Require at least one of the selected reference numbers to be present.

    `fields` are field_names as they appear in config/required_fields_config.json
    (e.g. "PO Reference", "Order Number", "Contract Number", "Work Order No.").
    """

    enabled: bool = True
    fields: list[str] = field(default_factory=lambda: ["PO Reference", "Order Number",
                                                        "Contract Number", "Work Order No."])
    mode: Literal["any", "all"] = "any"
    kind: Literal["reference"] = "reference"
    name: str = "Reference number"

    def evaluate(self, signals: dict) -> "RuleResult":
        refs = signals.get("references")
        if refs is None:
            return RuleResult(self.name, self.enabled, UNKNOWN,
                              "no OCR text available to check references")
        present = [f for f in self.fields if refs.get(f)]
        if self.mode == "all":
            ok = len(present) == len(self.fields)
        else:
            ok = len(present) > 0
        found = ", ".join(present) if present else "none found"
        return RuleResult(self.name, self.enabled, PASS if ok else FAIL,
                          f"require {self.mode} of {self.fields}; present: {found}")


@dataclass
class DateRangeRule:
    """Require the invoice date to fall within [start, end] (inclusive). ISO 'YYYY-MM-DD'."""

    enabled: bool = False
    start: str | None = None
    end: str | None = None
    kind: Literal["date"] = "date"
    name: str = "Invoice date range"

    def evaluate(self, signals: dict) -> "RuleResult":
        raw = signals.get("invoice_date")
        d = _parse_date(raw)
        if d is None:
            return RuleResult(self.name, self.enabled, UNKNOWN,
                              f"no parseable invoice date (raw={raw!r})")
        lo, hi = _parse_date(self.start), _parse_date(self.end)
        ok = (lo is None or d >= lo) and (hi is None or d <= hi)
        return RuleResult(self.name, self.enabled, PASS if ok else FAIL,
                          f"require {self.start}..{self.end}; invoice date {d.isoformat()}")


@dataclass
class PaymentTermsRule:
    """Require billing_due_days to satisfy `op` against `days` (e.g. '> 30')."""

    enabled: bool = True
    op: Literal[">", ">=", "<", "<=", "=="] = ">"
    days: int = 30
    kind: Literal["payment_terms"] = "payment_terms"
    name: str = "Payment terms (days)"

    def evaluate(self, signals: dict) -> "RuleResult":
        n = signals.get("billing_due_days")
        if n is None:
            return RuleResult(self.name, self.enabled, UNKNOWN,
                              "no payment-terms day count extracted")
        ok = _OPS[self.op](n, self.days)
        return RuleResult(self.name, self.enabled, PASS if ok else FAIL,
                          f"require days {self.op} {self.days}; found {n}")


_OPS = {
    ">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
}

RULE_CLASSES = {
    "visual": VisualRule, "reference": ReferenceRule,
    "date": DateRangeRule, "payment_terms": PaymentTermsRule,
}


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
@dataclass
class RuleResult:
    name: str
    enabled: bool
    status: Status
    explanation: str

    @property
    def passed(self) -> bool:
        # fail-closed: only an explicit PASS counts as satisfied
        return self.status == PASS


@dataclass
class VerdictResult:
    ready: bool
    rules: list[RuleResult]

    @property
    def n_pass(self) -> int:
        return sum(1 for r in self.rules if r.enabled and r.status == PASS)

    @property
    def n_enabled(self) -> int:
        return sum(1 for r in self.rules if r.enabled)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "n_pass": self.n_pass,
            "n_enabled": self.n_enabled,
            "rules": [asdict(r) | {"passed": r.passed} for r in self.rules],
        }


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------
@dataclass
class Policy:
    name: str = "Custom"
    rules: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"name": self.name,
                "rules": [{"kind": r.kind, **asdict(r)} for r in self.rules]}

    @classmethod
    def from_dict(cls, d: dict) -> "Policy":
        rules = []
        for rd in d.get("rules", []):
            rd = dict(rd)
            kind = rd.pop("kind", None)
            rd.pop("name", None)  # name is a class default; don't fight it
            klass = RULE_CLASSES.get(kind)
            if klass is None:
                continue
            rules.append(klass(**rd))
        return cls(name=d.get("name", "Custom"), rules=rules)


def default_policy() -> Policy:
    """A sensible starting policy: visual (either) + reference (any) + payment terms > 30d.
    Date range is present but disabled by default."""
    return Policy(name="Default", rules=[
        VisualRule(enabled=True, mode="either"),
        ReferenceRule(enabled=True),
        DateRangeRule(enabled=False),
        PaymentTermsRule(enabled=True, op=">", days=30),
    ])


def preset_policies() -> dict[str, Policy]:
    """Named presets shipped with the app; the user can save more."""
    return {
        "Default": default_policy(),
        "Strict": Policy(name="Strict", rules=[
            VisualRule(enabled=True, mode="both"),
            ReferenceRule(enabled=True, mode="any"),
            DateRangeRule(enabled=False),
            PaymentTermsRule(enabled=True, op=">", days=30),
        ]),
        "Lenient": Policy(name="Lenient", rules=[
            VisualRule(enabled=True, mode="either"),
            ReferenceRule(enabled=False),
            DateRangeRule(enabled=False),
            PaymentTermsRule(enabled=False),
        ]),
    }


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
def evaluate(signals: dict, policy: Policy) -> VerdictResult:
    """Judge one invoice's `signals` against `policy`.

    Verdict = AND of all ENABLED rules. Fail-closed: an enabled rule that returns UNKNOWN
    counts as not-satisfied, so the invoice is NOT READY.
    """
    results = [r.evaluate(signals) for r in policy.rules]
    enabled = [r for r in results if r.enabled]
    ready = len(enabled) > 0 and all(r.passed for r in enabled)
    return VerdictResult(ready=ready, rules=results)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _parse_date(value: Any) -> _dt.date | None:
    """Best-effort parse of a date string/date into a datetime.date."""
    if value is None or value == "":
        return None
    if isinstance(value, _dt.date):
        return value
    if isinstance(value, _dt.datetime):
        return value.date()
    s = str(value).strip()
    fmts = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d",
            "%d/%m/%y", "%m/%d/%y", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y"]
    for fmt in fmts:
        try:
            return _dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None
