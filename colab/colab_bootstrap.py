"""
colab_bootstrap.py — shared Colab runtime helper for the invoice-image-processing project.

This repository has **no git remote** (it's a local-only checkout), so a Colab notebook
cannot `git clone` it. Instead, every Colab notebook expects a snapshot of this repo's
`src/` + `scripts/` folders to already be sitting under `<drive_root>/code/` in the user's
Google Drive (copied there once -- e.g. zip the repo locally and unzip into Drive, or use
Google Drive Desktop sync), alongside an `inputs/` tree holding the processed data
(Rolando's real invoice manifest + images) that earlier pipeline stages produced.

Google Drive layout (default root `MyDrive/DL2_InvoiceAI/`):

    DL2_InvoiceAI/
    |-- code/                     # snapshot of repo src/ + scripts/
    |-- inputs/
    |   |-- invoice_manifest.csv  # Rolando's real 750-row manifest
    |   |-- images/               # the 750 real invoice JPGs (~218 MB)
    |   |-- annotations/          # the 3 batch annotation CSVs
    |   `-- upstream/<member>/    # earlier stages' outputs a later notebook consumes
    |-- outputs/
    |   |-- <member>/{predictions,metrics,figures,models,logs}/
    |   `-- _shared/{model_comparison,evaluation,report_assets}/
    `-- runs/<member>/<UTC-timestamp>/   # immutable per-run archive of this run's artifacts

Raw source datasets (e.g. SignverOD, StaVer, or the raw invoice scans) are NOT expected to
live in Drive -- they're pulled fresh from Kaggle inside each notebook that needs them (via
`kaggle.json` + `scripts/download_datasets.py`), since they're multi-GB and regenerable.

Typical notebook usage, in order:

    from colab_bootstrap import mount_drive, setup_paths, install_deps, verify_inputs, publish

    root = mount_drive()                       # mounts Drive, creates the output tree
    paths = setup_paths(root)                  # puts <root>/code on sys.path
    install_deps("ultralytics", "kaggle")      # pip install what this stage needs
    verify_inputs([paths.inputs / "invoice_manifest.csv"])   # fail fast, not deep in a cell

    from src.compute_profile import get_profile
    ... do the actual work, writing local outputs as usual ...

    publish("diana", local_predictions_csv, "predictions", paths=paths)

Designed to be import-safe and a no-op *mount* outside Colab (e.g. when smoke-tested on a
local machine): `mount_drive()` just resolves/creates a plain local folder instead of calling
`google.colab.drive.mount(...)`, so this module -- and any notebook cell that imports it --
can be exercised without a Colab runtime.
"""

from __future__ import annotations

import datetime as _dt
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ROOT = "/content/drive/MyDrive/DL2_InvoiceAI"

# Standard subfolders created under outputs/<member>/ and outputs/_shared/<kind>/.
_OUTPUT_KINDS = ("predictions", "metrics", "figures", "models", "logs")
_SHARED_KINDS = ("model_comparison", "evaluation", "report_assets")


def _in_colab() -> bool:
    return "google.colab" in sys.modules


def mount_drive(root: str | Path = DEFAULT_ROOT) -> Path:
    """Mount Google Drive (in Colab) and return the resolved project root, creating the
    expected `inputs/`, `outputs/`, `runs/` tree if it doesn't exist yet.

    No-op mount outside Colab -- `root` is just resolved/created as a plain local folder, so
    this function (and anything built on it) can be smoke-tested off of Colab.
    """
    root = Path(root)

    if _in_colab():
        from google.colab import drive  # type: ignore

        drive.mount("/content/drive", force_remount=False)
    else:
        print(f"[colab_bootstrap] Not running in Colab -- treating '{root}' as a local folder.")

    (root / "code").mkdir(parents=True, exist_ok=True)
    (root / "inputs" / "upstream").mkdir(parents=True, exist_ok=True)
    (root / "outputs" / "_shared").mkdir(parents=True, exist_ok=True)
    for kind in _SHARED_KINDS:
        (root / "outputs" / "_shared" / kind).mkdir(parents=True, exist_ok=True)
    (root / "runs").mkdir(parents=True, exist_ok=True)

    print(f"[colab_bootstrap] Project root: {root}")
    return root


@dataclass
class ColabPaths:
    """Small path-resolution helper, analogous in spirit to `src.config.PATHS` but rooted at
    the Google Drive project folder instead of a local git checkout."""

    root: Path

    @property
    def code(self) -> Path:
        return self.root / "code"

    @property
    def inputs(self) -> Path:
        return self.root / "inputs"

    def outputs(self, member: str) -> Path:
        """`<root>/outputs/<member>/` -- creates the standard {predictions, metrics, figures,
        models, logs} subfolders on first access."""
        d = self.root / "outputs" / member
        for kind in _OUTPUT_KINDS:
            (d / kind).mkdir(parents=True, exist_ok=True)
        return d

    def run_dir(self, member: str, timestamp: str | None = None) -> Path:
        """`<root>/runs/<member>/<UTC-timestamp>/` -- a fresh, immutable archive folder for
        this run's artifacts. A new UTC timestamp is generated per call unless one is passed
        explicitly (pass the same value across several `publish()` calls in one run so they
        land in the same archive folder)."""
        ts = timestamp or _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        d = self.root / "runs" / member / ts
        d.mkdir(parents=True, exist_ok=True)
        return d

    def shared(self, kind: str) -> Path:
        """`<root>/outputs/_shared/<kind>/` -- e.g. 'model_comparison', 'evaluation',
        'report_assets'."""
        d = self.root / "outputs" / "_shared" / kind
        d.mkdir(parents=True, exist_ok=True)
        return d


def setup_paths(root: str | Path) -> ColabPaths:
    """Put `<root>/code` on `sys.path` (so `from src.compute_profile import get_profile` and
    friends work exactly as they do in the local repo checkout) and return a `ColabPaths`."""
    root = Path(root)
    code_dir = str(root / "code")
    if code_dir not in sys.path:
        sys.path.insert(0, code_dir)
    return ColabPaths(root=root)


def install_deps(*extras: str) -> None:
    """pip install the given package specs (e.g. `install_deps("ultralytics", "kaggle")`).
    Safe to call even if some/all are already installed -- pip no-ops quickly in that case."""
    if not extras:
        return
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *extras], check=False)


def verify_inputs(required: list) -> None:
    """Hard-fail with a clear, actionable message naming every missing required input
    file/folder, rather than letting the notebook fail confusingly deep inside some later
    cell. Call this right after `setup_paths()`, before doing any real work."""
    missing = [p for p in required if not Path(p).exists()]
    if missing:
        listing = "\n".join(f"  - {p}" for p in missing)
        raise FileNotFoundError(
            "colab_bootstrap.verify_inputs: required input(s) not found:\n"
            f"{listing}\n\n"
            "Fix by either:\n"
            "  (a) copying/syncing the missing file(s) into Google Drive at the path(s) "
            "above (see colab/README.md for the expected Drive layout), or\n"
            "  (b) running the upstream member's notebook that produces it and re-publishing "
            "its output into Drive via colab_bootstrap.publish()."
        )


def publish(
    member: str,
    src_path: str | Path,
    kind: str,
    paths: "ColabPaths | None" = None,
    root: "str | Path | None" = None,
    run_timestamp: str | None = None,
) -> tuple[Path, Path]:
    """Copy a finished artifact into BOTH the 'latest' output location
    (`outputs/<member>/<kind>/<filename>`) and an immutable per-run archive location
    (`runs/<member>/<timestamp>/<kind>/<filename>`), so re-running a notebook never silently
    clobbers a previous run's results without a trace.

    `kind` should normally be one of predictions/metrics/figures/models/logs (the standard
    output subfolders), but any string is accepted -- a subfolder is created on demand.

    Pass either `paths` (a `ColabPaths` you already built via `setup_paths`) or `root` (a
    Drive root path, from which a `ColabPaths` is built for you).

    Returns (latest_path, archived_path).
    """
    src_path = Path(src_path)
    if not src_path.exists():
        raise FileNotFoundError(f"colab_bootstrap.publish: source path does not exist: {src_path}")

    if paths is None:
        if root is None:
            raise ValueError("publish() needs either `paths=` or `root=`.")
        paths = ColabPaths(root=Path(root))

    latest_dir = paths.outputs(member) / kind
    latest_dir.mkdir(parents=True, exist_ok=True)
    archive_dir = paths.run_dir(member, timestamp=run_timestamp) / kind
    archive_dir.mkdir(parents=True, exist_ok=True)

    def _copy(dst_dir: Path) -> Path:
        dst = dst_dir / src_path.name
        if src_path.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src_path, dst)
        else:
            shutil.copyfile(src_path, dst)
        return dst

    latest = _copy(latest_dir)
    archived = _copy(archive_dir)
    print(f"[colab_bootstrap] Published {src_path.name} -> {latest}  (+ archived to {archived})")
    return latest, archived
