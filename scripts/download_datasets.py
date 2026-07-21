"""
download_datasets.py

Downloads the Kaggle datasets used by this project and unzips them into the expected
data/raw/ subfolders.

------------------------------------------------------------------------------------
Kaggle API setup (do this once before running this script):

Local machine:
    1. Kaggle account -> Account -> "Create New API Token" -> downloads kaggle.json
    2. Place it at:
         Linux/Mac: ~/.kaggle/kaggle.json   (chmod 600 ~/.kaggle/kaggle.json)
         Windows:   C:\\Users\\<you>\\.kaggle\\kaggle.json

Google Colab (run this in a cell before calling this script):
    from google.colab import files
    files.upload()   # choose your kaggle.json

    import os, pathlib, shutil
    pathlib.Path("/root/.kaggle").mkdir(exist_ok=True)
    shutil.move("kaggle.json", "/root/.kaggle/kaggle.json")
    os.chmod("/root/.kaggle/kaggle.json", 0o600)

Never commit kaggle.json to git (it is excluded in .gitignore).
------------------------------------------------------------------------------------

Usage:
    python scripts/download_datasets.py --dataset invoices
    python scripts/download_datasets.py --dataset ocr_multitype
    python scripts/download_datasets.py --dataset signatures
    python scripts/download_datasets.py --dataset stamps
    python scripts/download_datasets.py --dataset invoice_ocr_fallback
    python scripts/download_datasets.py --dataset all
"""

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

# Repo root is the parent of this scripts/ folder.
REPO_ROOT = Path(__file__).resolve().parent.parent

# Dataset registry: CLI slug -> where it should end up under data/raw/.
DATASETS = {
    "invoices": {
        "slug": "osamahosamabdellatif/high-quality-invoice-images-for-ocr",
        "target_dir": "data/raw/invoices",
    },
    "ocr_multitype": {
        "slug": "senju14/ocr-dataset-of-multi-type-documents",
        "target_dir": "data/raw/invoices_ocr_multitype",
    },
    "signatures": {
        "slug": "victordibia/signverod",
        "target_dir": "data/raw/signatures",
    },
    "stamps": {
        "slug": "rtatman/stamp-verification-staver-dataset",
        "target_dir": "data/raw/stamps",
    },
    # Optional fallback — not included in --dataset all, fetch explicitly if needed.
    "invoice_ocr_fallback": {
        "slug": "senju14/invoice-ocr",
        "target_dir": "data/raw/invoices_fallback",
    },
}

# Datasets pulled by "--dataset all" (fallback is intentionally excluded).
DEFAULT_ALL = ["invoices", "ocr_multitype", "signatures", "stamps"]


def check_kaggle_api_configured() -> bool:
    """Return True if the kaggle CLI is installed and a credentials file exists."""
    if shutil.which("kaggle") is None:
        print(
            "[ERROR] The 'kaggle' CLI was not found on PATH.\n"
            "        Install it with: pip install kaggle\n"
            "        (It is already listed in requirements.txt.)"
        )
        return False

    candidate_paths = [
        Path.home() / ".kaggle" / "kaggle.json",
        Path("/root/.kaggle/kaggle.json"),  # common Colab location
    ]
    if not any(p.exists() for p in candidate_paths):
        print(
            "[ERROR] kaggle.json not found in any of:\n"
            + "\n".join(f"         - {p}" for p in candidate_paths)
            + "\n         See the setup instructions at the top of this script, "
            "or dataset_sources.md."
        )
        return False

    return True


def ensure_target_dir(target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)


def download_one(name: str, info: dict) -> bool:
    """Download + unzip a single dataset. Returns True on success, False on failure."""
    slug = info["slug"]
    target_dir = REPO_ROOT / info["target_dir"]
    ensure_target_dir(target_dir)

    print(f"\n=== Downloading '{name}' ({slug}) -> {target_dir} ===")
    try:
        result = subprocess.run(
            [
                "kaggle", "datasets", "download",
                "-d", slug,
                "-p", str(target_dir),
                "--force",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print("[ERROR] Could not invoke the 'kaggle' CLI. Is it installed and on PATH?")
        return False

    if result.returncode != 0:
        print(f"[ERROR] kaggle download failed for '{name}':\n{result.stderr.strip()}")
        return False

    print(result.stdout.strip())

    # Unzip anything that was downloaded (kaggle CLI names the zip after the dataset).
    zips = list(target_dir.glob("*.zip"))
    if not zips:
        print(
            f"[WARN] No .zip file found in {target_dir} after download — the dataset "
            "may already be unzipped, or the download silently produced no file. "
            "Check the output above for hints."
        )
        return True  # not necessarily fatal

    for zip_path in zips:
        print(f"Unzipping {zip_path.name} ...")
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(target_dir)
        except zipfile.BadZipFile:
            print(f"[ERROR] {zip_path.name} is not a valid zip file — download may be incomplete.")
            return False
        # Keep the zip around is wasteful; remove after successful extraction.
        zip_path.unlink()

    print(f"[OK] '{name}' ready at {target_dir}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Download project Kaggle datasets.")
    parser.add_argument(
        "--dataset",
        required=True,
        choices=list(DATASETS.keys()) + ["all"],
        help="Which dataset to download, or 'all' for the four core datasets.",
    )
    args = parser.parse_args()

    if not check_kaggle_api_configured():
        return 1

    names = DEFAULT_ALL if args.dataset == "all" else [args.dataset]

    all_ok = True
    for name in names:
        ok = download_one(name, DATASETS[name])
        all_ok = all_ok and ok

    if not all_ok:
        print("\n[FAILED] One or more datasets did not download cleanly. See errors above.")
        return 1

    print("\n[DONE] All requested datasets downloaded successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
