# Showcase sample invoices

Pickable from the **Showcase** (and Live Demo) tab of the Streamlit app. Eight images covering the
full progression, so the demo runs end-to-end with no dataset download.

| File | Category | What it shows |
|---|---|---|
| `clean_1_invoice.jpg` | Clean (no marks) | Invoice no + date + total + seller/client. Completeness high; **Lenient** passes, Default/Strict fail (no PO, no mark). |
| `clean_2_invoice.jpg` | Clean (no marks) | same, different invoice |
| `clean_3_invoice.jpg` | Clean (no marks) | same, different invoice |
| `stamp_only_1_real.jpg` | Stamp only | **Real StaVer** document (German invoice) with a blue stamp — authentic detection example |
| `stamp_only_2_invoice.jpg` | Stamp only | Composite: clean invoice + PO No + **stamp** → Default passes, Strict needs both marks |
| `signature_only_1_real.png` | Signature only | **Real SignverOD** letter with a handwritten signature — authentic detection example |
| `signature_only_2_invoice.jpg` | Signature only | Composite: clean invoice + PO No + **signature** |
| `both_stamp_and_signature.jpg` | Both | Composite: clean invoice + PO No + **stamp + signature** → passes **Default AND Strict**, completeness 100 |

## Notes for the deploy team
- **Two are real dataset images** (`*_real.*`, from StaVer / SignverOD) — genuine stamp/signature
  detection targets. The rest are **demo composites**: a real invoice with a real stamp/signature
  (and a `PO No:` line) overlaid, built to demonstrate the pipeline's "Ready" path. They are demo
  assets — the honest finding on the real 750-invoice corpus (no marks → strict ~0%) lives in the
  Batch/Model-Report views and the written report.
- **Detection requires the weights in `models/`**: `region_detector/best.pt` (regions/total →
  completeness) and `stamp_detector/best.pt` + `signature_detector/best.pt` (visual marks → Strict).
  Without the stamp/signature weights, the visual rules stay "unknown" and Strict won't flip.
- Want more/other real samples? Pull a few from `inputs/datasets/stamps` (StaVer) and
  `inputs/datasets/signatures` (SignverOD) on Drive and drop them here — the selector lists any
  image in this folder automatically.
