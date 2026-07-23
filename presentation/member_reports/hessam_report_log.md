# Report Log — Hessam (PM, Solution Architect, Integration Lead, Streamlit App Lead)

_Last updated: 2026-07-23 (final — integration complete, all upstream stages verified)._

## 1. Objective (what I was responsible for)
Architect the solution, orchestrate the member agents, integrate all outputs into the final
per-invoice JSON, build the Streamlit demo, and assemble the report + slide deck.

## 2. What I did
- Designed and scaffolded the full repository (folders, config, scripts, 14 `src/` modules,
  6 notebooks, member READMEs, Streamlit app, docs, agent prompts).
- Defined the output/interface contract so member outputs integrate cleanly.
- Set up orchestration/resume tooling (`ai_cowork/ORCHESTRATION.md`, job log, status log,
  `CLAUDE.md`) so work survives session interruptions.
- Deployed member agents in dependency order (Rolando first, then Diana/Jordan/Damir in parallel,
  then integration last).
- Fused Diana's (`stamp_signature_predictions.csv`), Jordan's (`region_predictions.csv`), and
  Damir's (`parameter_presence_results.csv`, `terms_extraction_results.csv`) outputs into **750**
  per-invoice JSON records in `outputs/final_json/sample_invoice_outputs/`, joined by
  `document_id` per `model_interface_contract.md` §5.
- Built and unit-tested `src/verdict_engine.py` — the fail-closed, user-configurable readiness
  policy engine (9/9 tests passing) — and the Streamlit application's three views (Live Demo,
  Batch Gallery, Model Report).
- Re-derived invoice-level reference/date/payment-terms signals at integration time by re-running
  Damir's own shared `parameter_checker.py` / `terms_extraction.py` modules against invoice OCR
  text and batch_1 annotation text, since Damir's published CSVs are keyed to the receipt dataset,
  not the 750 invoices.

## 3. Approach & key decisions
- Detection-first pipeline (detect regions → OCR only crops), SSD as the taught concept with a
  documented YOLOv8 fallback allowed for implementation.
- Integration happens at the CSV/JSON layer, not the model-object layer, so members can use
  different frameworks independently.
- **The verdict engine separates signal extraction from policy judgment.** Every upstream stage
  only ever produces signals (a detection, a presence flag, a date); the user assembles those
  signals into a policy (which rules are enabled, and how strict) entirely independently, so the
  same pipeline output can serve a compliance officer, an AP clerk, and an auditor without any
  code change — only a different policy configuration.
- **Fail-closed as the default semantics.** An enabled rule with no available signal for a given
  invoice counts as `unknown → fail`, never a silent pass — the right default for a readiness gate
  that must never confirm something it cannot actually verify.

## 4. Challenges faced & how I handled them
- **Challenge:** Public datasets lack several required region labels (terms/payment/reference/
  line-items/total). **Resolution:** Jordan solved this by fuzzy-matching the OCR Dataset's
  unlabelled text boxes against its labelled entity values, avoiding a manual annotation subset
  entirely.
- **Challenge:** Data availability depends on Kaggle credentials. **Resolution:** Rolando's
  ingestion stage works from the real invoice batches already present in the repo, so the pipeline
  stays runnable end-to-end without live Kaggle access.
- **Challenge:** Damir's `parameter_presence_results.csv` / `terms_extraction_results.csv` are
  keyed to the OCR-Dataset receipt IDs, not the 750 manifest invoices, since that's the dataset he
  has real ground truth against.
  - **Resolution / status:** Re-run Damir's own shared functions, unmodified, against invoice OCR
    text and batch_1 annotation text at integration time — this keeps Damir's evaluated numbers
    honest to what he actually measured while still giving the app real per-invoice signals to
    judge against.
- **Challenge:** The visual-mark rule fails closed for the entire batch, since Diana's detector
  finds 0/750 stamps or signatures on this invoice corpus.
  - **Resolution / status:** Reported this plainly rather than hiding it — it is a correct,
    honest consequence of the corpus (clean, unsigned digital templates) and Diana's held-out IoU
    (0.822 stamp / 0.815 signature) shows the detector itself works; the readiness-by-policy
    numbers below make the effect visible and explainable rather than surprising.

## 5. Results & metrics
From `outputs/reports/final_pipeline_report.md` and `outputs/final_json/sample_invoice_outputs/`:

- **750** per-invoice JSON records produced (one per manifest invoice).
- **Obligation-readiness by policy** (750 invoices each):

| Policy | Ready | of | % |
|---|---|---|---|
| Lenient | 750 | 750 | 100.0% |
| Default | 475 | 750 | 63.3% |
| Strict | 0 | 750 | 0.0% |

- **Region detections on invoices** (Jordan, `source=invoice`, total boxes across 750 invoices):
  other_text 54,009; address 1,877; company 1,437; total 1,389; date 50.
- Diana's region mean IoU: 0.822 (stamp) / 0.815 (signature). Jordan's macro mean IoU: 0.873.
  Damir's CER/WER: 0.2152 / 0.5423 (receipts, primary) and 0.0002 (invoices, secondary).

## 6. Assumptions & limitations
- **Fail-closed semantics mean "Not-ready" is not one thing.** It always includes both genuinely
  failing invoices and invoices the pipeline simply could not evaluate (`unknown`); the app's
  per-rule breakdown always distinguishes the two rather than conflating them.
- **Verdict rules do not depend on Jordan's region labels directly** — his `company`/`date`/
  `address`/`total`/`other_text` vocabulary is a receipt-entity schema, not the obligation-region
  schema in `config/label_schema.json`, so that mismatch is deliberately kept off the verdict's
  critical path (it still powers a "detected regions" panel and region-guided crop-then-OCR).
- **Batch-path coverage for reference/date/payment-terms signals is bounded by available OCR or
  annotation text**, not the full 750, since those signals are derived at integration time from
  text that not every invoice has at equal quality.
- **Payment-terms coverage is a corpus limitation, not an engine bug:** only 0.4% of invoices carry
  day-based terms phrasing, so the payment-terms rule is `unknown → fail-closed` for nearly all of
  them whenever a policy enables it.

## 7. Handoff notes (for downstream members / integration)
_N/A — I am the integration endpoint. Notes here are for the report/deck assembly stage: the
final JSON schema, verdict engine, and Streamlit app are all documented in
`model_interface_contract.md` and `src/verdict_engine.py` directly._

## 8. Figures / artifacts to consider for the slide deck
- `presentation/images/readiness_by_policy.png` — the 100% / 63.3% / 0% readiness spread across
  Lenient / Default / Strict policies, annotated with the honest Strict=0% explanation.
- `presentation/images/compute_profiles.png` — Diana's vs. Jordan's Colab T4 wall-clock/epoch/
  imgsz budget comparison, from each metrics JSON's `_run` provenance block.
- `presentation/images/metrics_per_class.png` — cross-member metrics summary chart.
- A Streamlit app screenshot (Live Demo verdict card, Batch Gallery roll-up) if captured live
  during the presentation.
