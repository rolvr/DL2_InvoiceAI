# Sample images for the Streamlit demo

Upload these in the **Live Demo** view.

| File | What it demonstrates |
|---|---|
| `invoice_clean_01/02/03` | Real clean invoices — region detection fires; the verdict runs on reference + date signals. The visual rule (if enabled) correctly reports *no mark* — these digital templates are unsigned. |
| `signed_document_example.png` | A signature document (SignverOD) — shows Diana's **signature** detector firing, so the visual rule can flip to pass. |
| `stamped_document_example.jpg` | A stamp scan (StaVer, downscaled) — shows the **stamp** detector firing. |

The clean invoices show the everyday path; the two document samples show the visual detector works when a mark is actually present.
