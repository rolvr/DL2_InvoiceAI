# Colab notebooks — how to run

This project's local development machine is CPU-only, so every member also gets a Colab copy
of their notebook that runs the same code path with a generous GPU compute budget
(`IIP_COMPUTE_PROFILE=colab_gpu`, see `src/compute_profile.py`). These notebooks live in
`colab/notebooks/` and are **unexecuted by design** on the local machine (no GPU here) — they
are meant to be opened and run in Colab by whoever wants the full-budget result.

## No git remote — code comes from Google Drive, not `git clone`

This repository is local-only (no GitHub/GitLab remote), so a Colab notebook cannot
`git clone` it. Instead:

1. On your local machine, zip (or Drive-sync) this repo's `src/` and `scripts/` folders.
2. Upload/unzip them into your Google Drive at `MyDrive/DL2_InvoiceAI/code/src/` and
   `MyDrive/DL2_InvoiceAI/code/scripts/`.
3. Each Colab notebook's bootstrap cell calls `colab_bootstrap.setup_paths(root)`, which puts
   `<root>/code` on `sys.path`, so `from src.compute_profile import get_profile` (etc.) works
   in Colab exactly like it does in a local checkout.

`colab/colab_bootstrap.py` itself is small enough to be pasted directly into a Colab cell, or
uploaded once to `MyDrive/DL2_InvoiceAI/code/colab_bootstrap.py` and imported.

## Expected Google Drive layout

Default root: `MyDrive/DL2_InvoiceAI/` (configurable — pass a different `root` to
`colab_bootstrap.mount_drive()` if your project folder lives elsewhere).

```
DL2_InvoiceAI/
├── code/                     # snapshot of repo src/ + scripts/ (+ colab_bootstrap.py)
├── inputs/
│   ├── invoice_manifest.csv  # Rolando's real 750-row manifest
│   ├── images/               # the 750 real invoice JPGs (~218 MB)
│   ├── annotations/          # the 3 batch annotation CSVs
│   └── upstream/<member>/    # earlier stages' outputs a later notebook consumes
├── outputs/
│   ├── <member>/{predictions,metrics,figures,models,logs}/   # "latest" copy per member
│   └── _shared/{model_comparison,evaluation,report_assets}/ # cross-member artifacts
└── runs/<member>/<UTC-timestamp>/   # immutable per-run archive (never clobbered)
```

- **Raw source datasets are NOT stored in Drive** (SignverOD, StaVer, the raw invoice scans,
  etc. are several GB). Each notebook that needs raw data downloads it fresh from Kaggle,
  in-notebook, via a `kaggle.json` upload + `python scripts/download_datasets.py --dataset
  <name>`.
- **Processed/intermediate data** (Rolando's manifest + images, other members' prediction
  CSVs) DOES live in Drive under `inputs/`, since later notebooks depend on it and
  regenerating it from scratch every time would be wasteful.
- `colab_bootstrap.publish(member, path, kind)` writes to both `outputs/<member>/<kind>/`
  (the latest copy — what downstream notebooks read from `inputs/upstream/<member>/`, once
  copied over) and `runs/<member>/<timestamp>/<kind>/` (an immutable archive of that run), so
  re-running a notebook never silently overwrites a previous run's results without a trace.

## Run order

The five notebooks have a dependency chain (mirrors `model_interface_contract.md`):

1. **01 — Rolando** (data ingestion): produces `invoice_manifest.csv` + invoice images.
   Downstream notebooks need these copied into `inputs/`.
2. **02 — Diana** (stamp/signature detection): reads the manifest from `inputs/`, downloads
   SignverOD + StaVer from Kaggle itself, trains, and publishes stamp/signature predictions.
3. **03 — Jordan** (region detection / IoU): reads the manifest, publishes region predictions.
4. **04 — Damir** (OCR / terms extraction): reads Jordan's region predictions + Diana's
   stamp/signature predictions from `inputs/upstream/`.
5. **05 — Hessam** (integration / Streamlit): reads everyone's outputs, builds the final JSON
   + report.

Each member's Colab notebook is independent and re-runnable on its own once its upstream
inputs exist in Drive — you do not need to run all five in the same session.

## Quick start (per notebook)

```python
# Cell 1 — pin the compute profile
import os
os.environ["IIP_COMPUTE_PROFILE"] = "colab_gpu"

# Cell 2 — bootstrap
from colab_bootstrap import mount_drive, setup_paths, install_deps, verify_inputs, publish
root = mount_drive()                 # default: MyDrive/DL2_InvoiceAI
paths = setup_paths(root)
install_deps("ultralytics")

# Cell 3 — verify inputs exist before doing real work
verify_inputs([paths.inputs / "invoice_manifest.csv"])

# ... notebook-specific work, using src.compute_profile.get_profile() for all knobs ...

# Last cell — publish outputs to Drive (in addition to writing local outputs/ as usual)
publish("diana", local_predictions_csv_path, "predictions", paths=paths)
```
