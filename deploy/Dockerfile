# Isolated deployment image for the Streamlit Showcase (Parts 4+5).
# Self-contained: copies ONLY what the Showcase needs (app/src/config/models). Does not touch
# the rest of the repo or the existing setup. Build from the REPO ROOT:
#   docker build -f deploy/Dockerfile -t invoice-streamlit .
FROM python:3.11-slim

# System libraries opencv-headless + torch need at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 libgl1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

# Python deps first (layer cache). requirements-deploy.txt lives at repo root.
COPY requirements-deploy.txt ./
RUN pip install --no-cache-dir -r requirements-deploy.txt

# Copy ONLY what the Streamlit Showcase needs — keeps the image small and isolated.
COPY app/    ./app/
COPY src/    ./src/
COPY config/ ./config/
COPY models/ ./models/

# Pre-download EasyOCR models at build time so the first request needs no download.
RUN python -c "import easyocr; easyocr.Reader(['en'], gpu=False)"

ENV DL2_SHOWCASE_ONLY=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8080
# Shell form so ${PORT} (Cloud Run injects it; default 8080) expands.
CMD streamlit run app/streamlit_app.py \
    --server.port=${PORT:-8080} --server.address=0.0.0.0 \
    --server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false
