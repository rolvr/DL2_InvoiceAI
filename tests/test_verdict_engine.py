"""Unit tests for src/verdict_engine.py — pure logic, no Streamlit."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.verdict_engine import (  # noqa: E402
    DateRangeRule, PaymentTermsRule, Policy, ReferenceRule, VisualRule,
    default_policy, evaluate, preset_policies,
)

READY = {
    "stamp_detected": True, "signature_detected": False,
    "references": {"PO Reference": True, "Work Order No.": False},
    "invoice_date": "2025-06-15", "billing_due_days": 45,
}


def test_default_policy_ready():
    # Default now = reference (any) + parseable invoice date. READY satisfies both.
    v = evaluate(READY, default_policy())
    assert v.ready is True
    assert v.n_enabled == 2 and v.n_pass == 2


def test_payment_terms_rule():
    pol = Policy(rules=[PaymentTermsRule(enabled=True, op=">", days=30)])
    assert evaluate({"billing_due_days": 45}, pol).ready is True   # 45 > 30
    assert evaluate({"billing_due_days": 14}, pol).ready is False  # 14 !> 30
    assert evaluate({"billing_due_days": 14}, pol).rules[0].status == "fail"


def test_fail_closed_on_missing_signal():
    # references unknown (no OCR) -> reference rule unknown -> NOT READY
    sig = dict(READY, references=None)
    v = evaluate(sig, default_policy())
    assert v.ready is False
    ref = [r for r in v.rules if r.name == "Reference number"][0]
    assert ref.status == "unknown" and ref.passed is False


def test_disabled_rule_ignored():
    # a reference rule that WOULD fail (no refs present), disabled -> verdict ignores it
    pol = Policy(rules=[DateRangeRule(enabled=True), ReferenceRule(enabled=False)])
    v = evaluate({"invoice_date": "2025-01-01", "references": {}}, pol)
    assert v.ready is True


def test_visual_modes():
    both = Policy(rules=[VisualRule(mode="both")])
    assert evaluate({"stamp_detected": True, "signature_detected": True}, both).ready
    assert not evaluate({"stamp_detected": True, "signature_detected": False}, both).ready
    either = Policy(rules=[VisualRule(mode="either")])
    assert evaluate({"stamp_detected": False, "signature_detected": True}, either).ready


def test_reference_any_vs_all():
    sig = {"references": {"PO Reference": True, "Contract Number": False}}
    any_rule = Policy(rules=[ReferenceRule(fields=["PO Reference", "Contract Number"], mode="any")])
    all_rule = Policy(rules=[ReferenceRule(fields=["PO Reference", "Contract Number"], mode="all")])
    assert evaluate(sig, any_rule).ready is True
    assert evaluate(sig, all_rule).ready is False


def test_date_range():
    inside = Policy(rules=[DateRangeRule(enabled=True, start="2025-01-01", end="2025-12-31")])
    assert evaluate({"invoice_date": "2025-06-15"}, inside).ready is True
    assert evaluate({"invoice_date": "2024-06-15"}, inside).ready is False
    # unparseable date -> unknown -> fail-closed
    assert evaluate({"invoice_date": "garbage"}, inside).ready is False


def test_no_enabled_rules_is_not_ready():
    empty = Policy(rules=[VisualRule(enabled=False)])
    assert evaluate(READY, empty).ready is False


def test_policy_roundtrip():
    for name, pol in preset_policies().items():
        d = pol.to_dict()
        back = Policy.from_dict(d)
        assert back.name == pol.name
        assert len(back.rules) == len(pol.rules)
        # evaluating the reconstructed policy matches the original
        assert evaluate(READY, back).ready == evaluate(READY, pol).ready


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except Exception:
            print(f"  FAIL  {fn.__name__}")
            traceback.print_exc()
    print(f"\n{passed}/{len(fns)} passed")
    sys.exit(0 if passed == len(fns) else 1)
