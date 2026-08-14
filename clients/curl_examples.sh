#!/usr/bin/env bash
#
# curl_examples.sh — call & test the Invoice Obligation-Readiness API with curl.
#
# One of the three required test clients (curl / Postman / Python).
# Start the API first (from the repo root):
#     uvicorn app.api:app --reload --port 8000
#
# Then either run this whole script:  bash clients/curl_examples.sh path/to/invoice.png
# or copy individual commands below.
#
# Requires: curl. (Optional: `jq` for pretty JSON — commands still work without it.)

set -euo pipefail

BASE_URL="${INVOICE_API_URL:-http://localhost:8000}"
IMAGE="${1:-app/sample_invoices/sample.png}"   # pass an invoice image path as $1

# Pretty-print helper: use jq if available, else cat.
pp() { if command -v jq >/dev/null 2>&1; then jq .; else cat; fi; }

echo "############################################################"
echo "# 1) Service metadata — GET /"
echo "############################################################"
curl -sS "${BASE_URL}/" | pp
echo

echo "############################################################"
echo "# 2) Health check — GET /health"
echo "#    Shows which detectors have weights on disk."
echo "############################################################"
curl -sS "${BASE_URL}/health" | pp
echo

echo "############################################################"
echo "# 3) Preset readiness policies + required fields — GET /policies"
echo "############################################################"
curl -sS "${BASE_URL}/policies" | pp
echo

echo "############################################################"
echo "# 4) Predict on an invoice image — POST /predict (multipart)"
echo "#    OCR ON, default confidence."
echo "############################################################"
curl -sS -X POST "${BASE_URL}/predict" \
  -H "accept: application/json" \
  -F "file=@${IMAGE};type=image/png" | pp
echo

echo "############################################################"
echo "# 5) Predict with query params — higher confidence, OCR OFF, custom id"
echo "############################################################"
curl -sS -X POST "${BASE_URL}/predict?confidence=0.4&run_ocr=false&document_id=ACME-001" \
  -F "file=@${IMAGE};type=image/png" | pp
echo

echo "############################################################"
echo "# 6) Error handling — POST /predict with a non-image (expect HTTP 400)"
echo "############################################################"
echo "not an image" > /tmp/not_an_image.txt
curl -sS -o /dev/null -w "HTTP status: %{http_code}\n" \
  -X POST "${BASE_URL}/predict" -F "file=@/tmp/not_an_image.txt;type=image/png" || true
echo

echo "Done. (Swagger UI: ${BASE_URL}/docs)"
