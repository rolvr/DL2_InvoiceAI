# Deploy the Streamlit Showcase to GCP (isolated — won't touch the existing deployment)

This folder is a **self-contained deployment** of the Streamlit Showcase app. It builds only
`app/ + src/ + config/ + models/` into a container and runs it. Everything uses **new, uniquely
named** resources so it never overwrites an existing service/instance.

Covers the plan's **Part 4 (containerization)** and **Part 5 (cloud deploy)**.
*(Part 3 — the REST API + curl/Postman/Python clients — already lives in the main repo under
`app/api.py` + `clients/`; this deployment serves the Streamlit app, which is the client UI.)*

---

## Prerequisites (one-time)
- **Google Cloud SDK** (`gcloud`) installed + logged in: `gcloud auth login`
- A GCP **project with billing enabled**. Set it: `gcloud config set project YOUR_PROJECT_ID`
- Enable the APIs:
  ```bash
  gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
  ```

---

## Option A — Cloud Run (recommended: serverless, scales to zero, public URL)

Run these **from the repo root**:

```bash
# 1. Build the image from the isolated deploy/Dockerfile (context = repo root)
gcloud builds submit --config deploy/cloudbuild.yaml .

# 2. Deploy a NEW Cloud Run service (unique name -> does NOT touch any existing service)
gcloud run deploy invoice-streamlit-showcase \
  --image gcr.io/$(gcloud config get-value project)/invoice-streamlit \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi --cpu 2 \
  --timeout 600 \
  --session-affinity \
  --max-instances 2
```
- `--session-affinity` keeps a user pinned to one instance (Streamlit uses a websocket).
- `--memory 2Gi` — torch + EasyOCR + YOLO need headroom; 512Mi will OOM.
- `--allow-unauthenticated` makes it a public demo URL (gcloud prints the URL). Drop it for private.
- **New instance, no collision:** the service name `invoice-streamlit-showcase` is new — deploying
  it never affects a differently-named existing service. To spin up *another* separate one later,
  just change the name (e.g. `invoice-streamlit-showcase-v2`).

Update later = re-run both commands (same name → new revision, zero downtime). Roll back in the
Cloud Run console's Revisions tab.

---

## Option B — Compute Engine VM (the Module 5 path)

```bash
# 1. Build + push the image (same as Option A step 1)
gcloud builds submit --config deploy/cloudbuild.yaml .

# 2. Create a NEW VM (unique name)
gcloud compute instances create invoice-streamlit-vm \
  --zone us-central1-a --machine-type e2-standard-2 \
  --image-family debian-12 --image-project debian-cloud \
  --tags streamlit

# 3. Firewall rule for the app port (only if you don't already have one)
gcloud compute firewall-rules create allow-streamlit \
  --allow tcp:8501 --target-tags streamlit --source-ranges 0.0.0.0/0

# 4. SSH in, install Docker, run the container
gcloud compute ssh invoice-streamlit-vm --zone us-central1-a
#   (inside the VM):
sudo apt-get update && sudo apt-get install -y docker.io
sudo docker run -d -p 8501:8080 --restart unless-stopped \
  gcr.io/YOUR_PROJECT_ID/invoice-streamlit
#   then open http://<VM_EXTERNAL_IP>:8501
```
This creates a **new** VM + firewall rule — it won't disturb any existing instance (different
name/tags).

---

## Local test before deploying (optional, needs Docker Desktop)
```bash
docker build -f deploy/Dockerfile -t invoice-streamlit .
docker run -p 8080:8080 invoice-streamlit
# open http://localhost:8080
```

## Cost note
Cloud Run scales to **zero** when idle (you pay per request/CPU-second) — a few cents for a demo.
The Compute Engine VM bills while running, so **stop it** when not in use:
`gcloud compute instances stop invoice-streamlit-vm --zone us-central1-a`.

## Notes
- The image bakes in the model weights (`models/*.pt`) and EasyOCR models, so cold starts need no
  downloads.
- `DL2_SHOWCASE_ONLY=1` is set in the image, so the deployed app shows only the Showcase tab.
- Nothing here modifies the repo root or the existing app — it all builds from `deploy/`.
