# Hessam — Speaking Transcript
## Integration, Verdict Engine & the Streamlit App

*(~2–3 minutes. Read naturally — this is a script to internalize, not recite word for word.)*

---

Hi, I'm Hessam. Rolando, Diana, Jordan, and Damir each produce a piece of the picture — a
manifest, stamp/signature boxes, region boxes, and OCR'd text with extracted fields. My job is to
merge all four into one coherent record per invoice, and then build the piece the business
audience actually interacts with: a **user-configurable verdict** on whether that invoice is ready
to become a digital obligation record.

[SHOW: `model_interface_contract.md` — the final JSON schema]

Integration happens at a fixed JSON schema — `visual_elements`, `detected_regions`,
`required_parameters`, `payment_context`, `terms_and_conditions`, and a `pistacio_readiness`
block — joined across everyone's CSVs by `document_id`. One subtlety I want to flag directly:
Damir's parameter and terms CSVs are keyed to the **receipt** dataset he evaluates against, not
the 750 invoices. So the invoice-level reference, date, and payment-terms signals the app actually
uses are **derived at integration time** — I re-run Damir's own shared modules,
`parameter_checker.py` and `terms_extraction.py`, against invoice OCR text and the batch_1
annotation text. I didn't fork his logic; I reused it against a different input, so the results
stay traceable to one implementation.

[SHOW: `src/verdict_engine.py` — the Rule classes]

The headline feature is the **verdict engine**. Instead of one hardcoded "ready" rule, the user
builds a policy from four toggleable rule types before judging any invoice: a visual-mark rule
(stamp OR/AND signature), a reference-number rule (any of PO / Order / Contract / Work Order), an
invoice-date-range rule, and a payment-terms-days rule. The verdict is the **AND of every enabled
rule**. And critically, it's **fail-closed** — if a rule is enabled but there's no signal for a
given invoice, that counts as a fail, never a silent pass, and the breakdown always shows
"unknown — treated as fail" so nobody mistakes an unconfirmed check for a confirmed one. This
logic is pure Python, no Streamlit dependency, and it's unit-tested independently of the app.

[SHOW: the Streamlit app — Live Demo view]

The app itself has three views. **Live Demo** — upload or pick an invoice, see the annotated
boxes, get a verdict card with a per-rule breakdown, download the JSON. [SHOW: toggle a rule off
and on, watch the verdict flip live.] **Batch Gallery** — apply the same policy across all 750
invoices at once, see "N of 750 pass," filter, and export the passing set. **Model Report** — the
real metrics from every member plus a local-CPU-vs-Colab-GPU comparison, for the technical
audience.

[SHOW: `presentation/final_report.md` §5 Results — final tables]

Here's where it all lands. Diana: stamp precision/recall/mean-IoU 0.903/0.875/0.822, signature
0.894/0.638/0.815 — but 0 of 750 invoices actually have a detected mark, because this corpus is
unsigned digital templates. Jordan: per-class mean IoU from 0.812 (date) to 0.896 (address),
macro mean IoU 0.873, and unlike Diana's visual marks, region detections cover 750 of 750
invoices. Damir: CER 0.215 / WER 0.542 on the harder receipt test split, CER 0.0002 on the easier
clean invoices — always reported together. And the number I own directly: **the readiness spread
on the same 750 invoices — strict policies (Lenient 100%, Default ~0%, Strict 0%) plus a graded
completeness score (Ready 42%, Needs review 12%, Not ready 46%).** The strict Default is ~0%
because the corpus carries no PO/contract references — an honest domain gap; an earlier 63.3% there
was an artifact of loose string matching, since corrected. The configurable engine is the whole
point, and the graded score is what yields a meaningful spread when the strict gate can't — while
Strict=0% remains the fail-closed design working correctly on a corpus with no visual marks.

[SHOW: presentation/images/readiness_by_policy.png]
[SHOW: presentation/images/metrics_per_class.png]

---

## Likely Professor Q&A

**Q1: Why is a configurable verdict better than one fixed rule?**
A: Different roles need different thresholds for the same underlying signals — a compliance
officer might require both a stamp and a signature, while an AP clerk doing a first pass might
accept either. Hardcoding one rule forces every user into someone else's judgment call. Exposing
the rules as a policy the user builds means the same signals — stamp/signature detection,
reference presence, date, payment terms — serve every use case without touching code.

**Q2: What does "fail-closed" mean, and why is it the right default for a compliance gate?**
A: Fail-closed means that when an enabled rule has no evidence to evaluate — say, an invoice was
never OCR'd — the rule is treated as *not satisfied* rather than skipped or assumed true. For a
readiness gate feeding a compliance or finance workflow, silently passing something you can't
actually confirm is the dangerous failure mode; treating unconfirmed evidence as a fail, and
showing that distinction transparently in the breakdown, is the safer and more honest default.

**Q3: How do you compare the local-CPU run and the Colab-GPU run fairly?**
A: Every metrics JSON carries a `_run` provenance block — the compute profile name, epochs, image
size, batch size, device, and wall-clock time it took. Because both `local_cpu` and `colab_gpu`
pull their knobs from the same `src/compute_profile.py` module instead of being hand-tuned
separately in each notebook, a local dev run and a full Colab-GPU run can never silently diverge
in what they even mean — the report's compute-budget comparison table is built directly from these
`_run` blocks, so the comparison is apples-to-apples by construction.
