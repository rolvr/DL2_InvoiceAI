# Rolando — Speaking Transcript
## Data Ingestion & the Invoice Manifest

*(~2–3 minutes. Read naturally — this is a script to internalize, not recite word for word.)*

---

Hi, I'm Rolando, and I own the very first stage of this pipeline: turning a messy folder of raw
invoice scans into one clean, trustworthy table that everyone else on the team builds on. I don't
train a model — my job is data engineering — but I'd argue it's the stage the whole project's
honesty depends on. If my manifest is wrong, every metric downstream is wrong too.

[SHOW: `data/processed/invoice_manifest.csv` — a few rows]

What I produce is `invoice_manifest.csv`: one row per invoice, with `document_id`,
`image_path`, `width`, `height`, `split`, and `has_ground_truth`. That `document_id` is the join
key — every other member's prediction CSV keys off it, so if I get it wrong, nothing downstream
lines up.

Two decisions I made are worth walking through because they're real engineering trade-offs, not
just formalities.

[SHOW: the annotation-CSV directory listing, batch_1 only]

First — annotation-aware resampling. We have real ground-truth annotation CSVs, but only for
`batch_1`. When I first sampled invoices at random across all batches, only **26.3%** of my
sample had any ground truth at all — most of the invoices I picked simply had no labels to
evaluate against. So I resampled, deliberately preferring annotated images, and that took
coverage from 26.3% up to **100%** across a 750-row manifest, split 525 train / 120 val / 105
test. The honest cost is that I gave up some cross-batch visual variety to get there — a real
trade-off, and I'd make the same call again, because a model you can't evaluate is worse than a
model trained on a slightly narrower slice of data.

[SHOW: the duplicate-count comparison, 8,181 vs 5,201]

Second — and this is the one I'm proudest of catching — I found that `batch_3` secretly contains
copies of images already in `batch_1` and `batch_2`. If I hadn't checked, the true unique invoice
count would have looked like 8,181, but it's actually **5,201**. Sampling those duplicates would
have let the exact same invoice land in both a training split and a test split — that's data
leakage, and it would have quietly inflated every downstream evaluation number without anyone
noticing. I excluded the duplicates from sampling entirely.

Finally, I stratify the train/val/test split by ground-truth availability, so every split stays
fully labelled, not just the training set.

[SHOW: presentation/images/sample_invoice_grid.png]
[SHOW: presentation/images/preprocessing_examples.png]

That's the manifest. Garbage in, garbage out — and I made sure what goes in is clean.

---

## Likely Professor Q&A

**Q1: Why is data leakage dangerous, and how did you actually catch it here?**
A: Leakage happens when the same underlying example appears in both training and test data — the
model effectively gets to "see the answer" before being tested on it, which inflates metrics in a
way that won't hold up on genuinely new data. I caught it by comparing image content/filenames
across `batch_1`, `batch_2`, and `batch_3` and finding that `batch_3` wasn't new material — it was
copies of the first two batches. Excluding those duplicates from sampling keeps our train/val/test
splits genuinely independent.

**Q2: Why prefer annotated images over a purely random sample?**
A: Because a random sample across batches without annotations gave us images we could never score
— only 26.3% had any ground truth. An unscoreable dataset doesn't let downstream members report
real precision/recall/IoU numbers. Preferring annotated images trades some visual diversity for
the ability to actually evaluate the pipeline honestly, which I judged as the right trade for a
project where "can you back up your metric" matters.

**Q3: What would you do differently if you had annotations for every batch, not just batch_1?**
A: I'd go back to a purely random, batch-balanced sample instead of an annotation-aware one — that
would maximize visual variety while still keeping 100% ground-truth coverage, giving both Diana
and Jordan a broader, more representative training/eval distribution instead of one skewed toward
whatever batch_1 happens to contain.
