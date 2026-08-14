#!/usr/bin/env python3
"""
python_client.py — a small Python web client for the Invoice Obligation-Readiness API.

One of the three required test clients (curl / Postman / Python). Uses `requests`; talks to the
FastAPI service over HTTP exactly as an external consumer would.

Examples
--------
    # health + policies
    python clients/python_client.py health
    python clients/python_client.py policies

    # run one invoice through /predict (OCR on)
    python clients/python_client.py predict path/to/invoice.png

    # tweak the query params
    python clients/python_client.py predict invoice.png --confidence 0.4 --no-ocr --id ACME-001

    # point at a non-default host
    python clients/python_client.py --base-url http://localhost:8000 health

Requires: pip install requests
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys

import requests

DEFAULT_BASE_URL = os.environ.get("INVOICE_API_URL", "http://localhost:8000")


class InvoiceAPIClient:
    """Thin wrapper over the three endpoints."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health(self) -> dict:
        r = requests.get(f"{self.base_url}/health", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def policies(self) -> dict:
        r = requests.get(f"{self.base_url}/policies", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def predict(self, image_path: str, confidence: float = 0.25,
                run_ocr: bool = True, document_id: str | None = None) -> dict:
        if not os.path.isfile(image_path):
            raise FileNotFoundError(image_path)
        params = {"confidence": confidence, "run_ocr": str(run_ocr).lower()}
        if document_id:
            params["document_id"] = document_id
        mime = mimetypes.guess_type(image_path)[0] or "application/octet-stream"
        with open(image_path, "rb") as fh:
            files = {"file": (os.path.basename(image_path), fh, mime)}
            r = requests.post(f"{self.base_url}/predict", params=params,
                              files=files, timeout=self.timeout)
        r.raise_for_status()
        return r.json()


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def _summarize_prediction(res: dict) -> None:
    """A compact human-readable summary on top of the raw JSON."""
    c = res.get("completeness", {})
    print("\n--- summary -------------------------------------------------")
    print(f"document_id     : {res.get('document_id')}")
    print(f"image           : {res.get('image')}")
    print(f"completeness    : {c.get('score')}/100  ({c.get('tier')})")
    for name, v in res.get("verdicts", {}).items():
        flag = "READY" if v.get("ready") else "NOT READY"
        print(f"policy {name:8} : {flag}  ({v.get('n_pass')}/{v.get('n_enabled')} rules passed)")
    print(f"degraded        : {res.get('meta', {}).get('degraded')} "
          f"(True when weights/OCR absent -> fail-closed)")
    print("-------------------------------------------------------------")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Python client for the Invoice Readiness API.")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"default: {DEFAULT_BASE_URL}")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("health", help="GET /health")
    sub.add_parser("policies", help="GET /policies")

    pp = sub.add_parser("predict", help="POST /predict")
    pp.add_argument("image", help="path to an invoice image")
    pp.add_argument("--confidence", type=float, default=0.25)
    pp.add_argument("--no-ocr", dest="run_ocr", action="store_false", help="skip EasyOCR")
    pp.add_argument("--id", dest="document_id", default=None)

    args = p.parse_args(argv)
    client = InvoiceAPIClient(args.base_url)

    try:
        if args.command == "health":
            _print(client.health())
        elif args.command == "policies":
            _print(client.policies())
        elif args.command == "predict":
            res = client.predict(args.image, confidence=args.confidence,
                                 run_ocr=args.run_ocr, document_id=args.document_id)
            _print(res)
            _summarize_prediction(res)
    except requests.exceptions.ConnectionError:
        print(f"ERROR: could not reach the API at {args.base_url}. "
              f"Is it running?  (uvicorn app.api:app --port 8000)", file=sys.stderr)
        return 2
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e}\nbody: {e.response.text}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
