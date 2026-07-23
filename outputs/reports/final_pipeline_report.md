# Final Pipeline Integration Report

Fused **750** per-invoice JSON records from all four upstream stages into `outputs/final_json/sample_invoice_outputs/`.

## Obligation-readiness across the batch (by policy)

| Policy | Invoices Ready | of | % |
|---|---|---|---|
| Default | 475 | 750 | 63.3% |
| Strict | 0 | 750 | 0.0% |
| Lenient | 750 | 750 | 100.0% |

Default policy: **475 / 750 ready** (63.3%).

## Region detections on invoices (Jordan, `source=invoice`)

| Region label | Total boxes across 750 invoices |
|---|---|
| other_text | 54009 |
| address | 1877 |
| company | 1437 |
| total | 1389 |
| date | 50 |

## Honest integration notes

- **Visual rule fails-closed on the whole batch:** the invoice corpus is clean digital templates with no stamps or signatures (Diana: 0/750 detections), so any policy requiring a visual mark yields 0 ready. This is a property of the data, not a model failure (Diana's held-out stamp IoU 0.82 / signature IoU 0.81).
- Reference/date/terms signals are derived at integration from invoice OCR text + batch_1 annotation text (Damir's per-receipt CSVs are not invoice-keyed).
- `detected_regions` uses the contract's tracked labels; Jordan's richer receipt-entity labels are preserved under `region_detections_raw`.