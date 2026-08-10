# Hessam — Integration, Verdict & Readiness · Report Log

> Destination in repo: `presentation/member_reports/hessam_report_log.md`
> Numbers from the corrected pipeline: strict policies (notebook 05, `verdict_engine`) +
> graded completeness (notebook 06) over all 750 invoices, honest upstream signals.

## Role
Merge every member's outputs into per-invoice records and judge **obligation-readiness**. Two
complementary views: a strict, rule-based **verdict engine** (contractual gate) and a graded
**completeness score** (how field-complete each document is).

## Headline: the 63.3% was an artifact — here is the honest picture

The original "63.3% ready" was **not real**. It came from loose string matching in parameter
detection (a 2-letter `"po"` keyword matched words like "report"; catch-all regex matched phone
numbers). Corrected, the two honest views are:

### View 1 — Strict contractual policies (`src/verdict_engine.py`, fail-closed)
| Policy | Rule set | Ready |
|---|---|---|
| Strict | visual mark + reference + date | ~0% |
| Default | reference (PO/Order/Contract) + date | ~0% |
| Lenient | parseable date only | ~100% |

Default/Strict are ~0% because the corpus carries **no PO/contract references and no
stamps/signatures** — a real receipts→invoices / procurement domain gap, not a pipeline failure.

### View 2 — Graded completeness score (notebook 06, standardized rubric)
| Tier | Count | % |
|---|---|---|
| **Ready** (score ≥ 80) | 315/750 | **42.0%** |
| Needs review (60–79) | 93/750 | 12.4% |
| Not ready (< 60) | 342/750 | 45.6% |

Mean score **76.3 / 100**.

## The standardized rubric (config-driven, documented)
Weighted core fields (grounded in standard invoice requirements — supplier, unique number,
date, total): **total 25 · date 20 · reference 20 · counterparty 20 · readable 15** (+ bonus:
payment terms 10, visual mark 10; capped at 100). Thresholds: **Ready ≥ 80 · review ≥ 60**.

## Why it's honest (guardrails)
- **Fail-closed**: an enabled rule with no signal counts as fail; unknowns never pass.
- **Reference can't dominate**: capped at 20/100, and it only counts a **digit-bearing
  identifier** (≥ 2 digits). The audit confirmed matches are **real 8-digit invoice numbers**
  (e.g. `62312762`, `25796631`), not label mis-matches.
- **Per-field breakdown** saved for every invoice (`readiness_completeness_scores.csv`), fully
  auditable — no hidden weak signals.
- Verdict policy was **never loosened** to raise the number.

## Transparency note (say this out loud)
On this corpus, **date, reference, and readable text are near-universal** (a fixed 55-pt
baseline), so the readiness tier is effectively driven by whether Jordan's region detector found
a **total** (25) and a **counterparty/company** (20). "Ready" ≈ "a total region was detected"
(42% Ready ≈ 41.9% total-present). The score reflects region-detection recall, not fabricated
completeness.

## The reframed story for the deck
> The 750 are genuine **structured invoices** — they carry invoice numbers, dates, sellers, and
> totals — so under a field-completeness standard **42% are Ready** and 12% need review. What
> they lack is **B2B procurement references (PO/contract) and signatures/stamps**, so under a
> strict contractual policy **~0%** qualify. That gap — not document quality — is the real
> limitation. We also *found and fixed* a ~60-point inflation in the original metric, then
> measured truthfully.

## Caveats
- Diana's detector trained on SignverOD/StaVer (not invoices) → 0 marks here (domain gap).
- Jordan's regions trained on OCR-dataset receipts → transfer to full-page invoices imperfect;
  readiness tiers inherit its recall on `total`/`company`.
- Payment terms extracted for <1% (genuinely rare on this data).
- `batch_3` duplicates excluded from the 750 manifest to prevent train/test leakage.

## Q&A rehearsal
- **Why two readiness views?** A strict contractual gate and a graded completeness standard
  answer different questions ("is this a signable obligation?" vs "how complete is this record?").
- **Isn't accepting an invoice number gaming?** No — it's a real, auditable identifier, capped at
  20/100, requiring digits; it can't make a document Ready on its own.
- **Why is Default ~0%?** The data has no PO/contract references — honest domain gap, not a bug.
- **What changed the 63.3%?** It was a string-matching artifact; corrected matching + real
  per-invoice signals replaced it.
