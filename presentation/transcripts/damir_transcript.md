# Damir — Speaking Transcript
## OCR, Business Parameters & Terms Extraction

*(~2–3 minutes. Read naturally — this is a script to internalize, not recite word for word.)*

---

Hi, I'm Damir. Once Diana and Jordan know *where* the marks and regions are, my job is to actually
*read* the document and pull out the structured business facts a compliance check needs: does it
cite a PO or contract number, what are the payment terms, is there a due date, and does the terms
language mention anything like a late-payment penalty or a dispute clause.

[SHOW: an EasyOCR call on a sample crop]

For text extraction I use **EasyOCR**, a deep-learning OCR engine, run on GPU. I picked it over
Tesseract or PaddleOCR because it gives strong accuracy out of the box with minimal setup — a
reasonable accuracy-vs-speed-vs-setup trade for a project on a Colab time budget.

[SHOW: `config/required_fields_config.json`]

But OCR text alone isn't a structured answer. On top of it I run **rule-based extraction** — two
shared modules, `parameter_checker.py` and `terms_extraction.py` — rather than training another
model to pull out fields. I chose rule-based deliberately: it needs zero labelled training data
for these specific fields, every match is traceable to an exact keyword or regex pattern, which
matters when this feeds a compliance decision, and a user can add a brand-new required field —
say, an Insurance Certificate number — just by editing a config file, with no code change at all.

[SHOW: the CER/WER scoring cell]

Here's where I want to be really upfront about evaluation, because I have **two eval sets of very
different strength**, and I report both, always with context. My **primary** set is the OCR
Dataset's own test split — 973 documents, **100% coverage**, real per-box ground-truth
transcriptions — so I can compute genuine **CER** and **WER**, character and word error rate,
using `jiwer`. Lower is better. ⟪TBD: Damir primary CER/WER mean+median (from ocr_parameter_metrics.json → ocr_primary) —
landing once this run is verified.⟫

My **secondary** set is real full-page batch_1 invoices with ground-truth OCR text from the
annotation CSVs — a genuinely harder, more realistic check, but small, and I always state the
denominator out loud: only about **197 of the 750** manifest images have any ground truth at all,
because annotation CSVs exist only for batch_1. I'd rather say that number every time than let
someone assume the secondary check covers the whole dataset.

[SHOW: `outputs/predictions/parameter_presence_results.csv` and `terms_extraction_results.csv`]

For the business parameters — PO reference, order number, contract number, work order number, and
a few others — I check keyword and regex presence against the OCR'd text. For payment terms, I
pattern-match phrasings like "Net 30" or "due within 15 days" and separately flag late-payment,
dispute, and penalty language.

---

## Likely Professor Q&A

**Q1: What are CER and WER, and why do you report both?**
A: Character Error Rate and Word Error Rate both measure how far OCR output diverges from the
ground-truth transcription — roughly, the edit distance normalized by reference length — but at
different granularities. CER catches character-level noise (a "5" misread as an "S"), WER reflects
whether whole words come out usable for downstream parsing. I report both because a low CER can
still hide a high WER if errors cluster inside individual words.

**Q2: Why rule-based extraction on top of OCR instead of an end-to-end learned extractor?**
A: Three reasons: no labelled training data exists for fields like "PO Reference" or "Work Order
No." across our datasets, so a learned extractor would need annotation work we don't have; every
rule-based match is auditable back to a specific keyword or regex, which matters for something
feeding a compliance verdict; and a user can extend the field list live from config, with zero
retraining or code changes — an end-to-end model would require retraining for every new field.

**Q3: Which parameters are hardest to detect, and why does that matter for Pistac.io readiness?**
A: Reference numbers with free-form formats — contract numbers, work order numbers — are harder
than something like a date, because their patterns vary more between vendors and there's no single
canonical format to regex against. That matters directly for readiness: if a genuine PO reference
is present but OCR quality or format variation causes us to miss it, our fail-closed verdict engine
would mark that invoice Not-ready even though it should pass — which is why I always report the
denominator and coverage honestly, so the team understands where that risk concentrates.
