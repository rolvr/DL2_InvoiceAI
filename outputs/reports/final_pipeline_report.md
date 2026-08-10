# Final Pipeline Report

Corrected integration report — readiness computed with `src/verdict_engine.py` (fail-closed) over
**all 750 invoices**, plus a graded completeness score (notebook 06). This **supersedes an earlier
version whose "63.3%" was an artifact** of loose string matching in parameter detection (since
corrected).

## Obligation-readiness — two complementary views

### View 1 — strict rule-based policies (`verdict_engine`, fail-closed)
| Policy | Requires | Ready |
|---|---|---|
| Strict | visual mark + reference + date | ~0% |
| Default | reference (PO/Order/Contract) + date | ~0% |
| Lenient | parseable date only | ~100% |

Default/Strict are ~0% because the corpus carries **no PO/contract references and no
stamps/signatures** — the receipts→invoices / procurement **domain gap**, not a pipeline failure.

### View 2 — graded completeness score (standardized rubric, notebook 06)
| Tier | Count | % |
|---|---|---|
| Ready (score ≥ 80) | 315/750 | 42.0% |
| Needs review (60–79) | 93/750 | 12.4% |
| Not ready (< 60) | 342/750 | 45.6% |

Mean score **76.3 / 100**. Rubric (weighted, config-driven): total 25 · date 20 · reference 20 ·
counterparty 20 · readable 15 (+ bonus payment_terms 10, visual 10). Fail-closed; the reference
slot is capped at 20/100 and requires a digit-bearing invoice/document number (audited as real).

## Signal coverage (honest, all 750)
- Stamp/signature detected on invoices: **0 / 750** (no visual marks on this corpus)
- Any required reference (PO/Order/Contract): **~0 / 750**
- Parseable invoice date: **750 / 750**
- Payment-terms days extracted: **~6 / 750 (0.8%)**

## Detection quality (real held-out splits)
- **Diana** — stamp IoU 0.815 / signature IoU 0.819; stamp P/R ≈ 0.91/0.91.
- **Jordan** — region detection macro mean-IoU ≈ 0.87 (per-class 0.81–0.90).
- **Damir** — OCR CER 0.215 / WER 0.54 on the OCR-Dataset test split (98 docs, 100% GT).

## What changed vs the earlier report
The prior "Default 475/750 = 63.3%" was **inflated by loose parameter matching** (a 2-letter `"po"`
keyword matched words like "report"/"deposit"; catch-all regex matched phone numbers). Corrected
matching + real invoice-keyed signals replaced it — required references are honestly ~0%. We
*found and fixed* a ~60-point inflation and then measured truthfully.

## Caveats
- Diana's detector trained on SignverOD/StaVer (not invoices) → 0 marks here (domain gap).
- Jordan's regions trained on OCR-dataset receipts → transfer to full-page invoices imperfect;
  the completeness tiers largely track its recall on `total`/`company`.
- Payment terms extracted for <1% of invoices (genuinely rare on this data).
- `batch_3/` duplicates batches 1 & 2; excluded from the 750-row manifest to prevent train/test
  leakage (true unique invoice count is 5,201, not 8,181).
