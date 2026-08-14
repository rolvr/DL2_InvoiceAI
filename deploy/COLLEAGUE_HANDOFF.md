# Colleague Handoff — deploy the Streamlit as a SECOND service (API stays live)

**Goal:** run the Streamlit Showcase as a new container on the existing VM, on a new port,
**without touching** the FastAPI already live at `http://34.130.49.237:8000/docs`.

Everything is isolated: new image, new container name, new port, new firewall rule. The API
container is never stopped or modified.

---

## What you need
- You own the VM and the GCP project, so you run all the `gcloud` steps below.
- Values used here:
  - **Project:** `feisty-tempo-505518-b1`
  - **VM:** `nvoiceai-vm`  (confirm with `gcloud compute instances list` if unsure)
  - **Zone:** `northamerica-northeast2-c`
  - **VM external IP:** `34.130.49.237`
  - **New Streamlit port:** `8501`  (API keeps `8000`)
  - **Image:** `gcr.io/feisty-tempo-505518-b1/invoice-streamlit`
- No local Docker needed — the image is built in the cloud (Cloud Build).

### Dockerfile location + container port
- **Dockerfile:** `deploy/Dockerfile` (NOT the repo root). `deploy/cloudbuild.yaml` references it
  explicitly via `-f deploy/Dockerfile`.
- **Container port:** Streamlit listens on **8080** inside the container
  (`CMD ... --server.port=${PORT:-8080}`, `EXPOSE 8080`). So the Step 2 mapping
  **`-p 8501:8080`** is correct: host `8501` → container `8080`.
- `.gcloudignore` uses root-anchored `/Dockerfile` and `/requirements.txt` so it drops only the
  (now-deleted) root Dockerfile, never `deploy/Dockerfile`. The deploy Dockerfile and
  `requirements-deploy.txt` are always included in the build context.

---

## Step 1 — Build the image in the cloud (from a clone of the repo)
```bash
git clone https://github.com/rolvr/DL2_InvoiceAI.git
cd DL2_InvoiceAI

gcloud config set project feisty-tempo-505518-b1
gcloud services enable cloudbuild.googleapis.com containerregistry.googleapis.com artifactregistry.googleapis.com

gcloud builds submit --config deploy/cloudbuild.yaml .
```
Wait for `SUCCESS`. This pushes `gcr.io/feisty-tempo-505518-b1/invoice-streamlit`.
(A `.gcloudignore` in the repo makes sure the model weights `models/*.pt` are included in the build.)

Takes ~5–10 min the first time (PyTorch base image).

---

## Step 2 — On the VM: add swap, then run the container next to the API
```bash
gcloud compute ssh nvoiceai-vm --zone northamerica-northeast2-c
```
Then **inside the VM**:
```bash
# a) 4 GB swap — cushion so two torch apps coexist on the 3.8 GB VM (non-disruptive; API untouched)
sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
free -h        # should now show ~4.0Gi swap

# b) pull + run the Streamlit image (NEW name, NEW port — API container untouched)
gcloud auth configure-docker --quiet
sudo docker pull gcr.io/feisty-tempo-505518-b1/invoice-streamlit
sudo docker run -d --name invoice-streamlit --restart unless-stopped \
  -p 8501:8080 gcr.io/feisty-tempo-505518-b1/invoice-streamlit

sudo docker ps   # must list BOTH: the API (:8000) and invoice-streamlit (:8501)
```
Then `exit`.

---

## Step 3 — Open the new port (existing :8000 rule untouched)
```bash
gcloud compute firewall-rules create allow-streamlit-8501 \
  --project feisty-tempo-505518-b1 --network default \
  --allow tcp:8501 --source-ranges 0.0.0.0/0
```

---

## Step 4 — Verify both are live
- API (unchanged): `http://34.130.49.237:8000/docs`
- Streamlit (new): `http://34.130.49.237:8501`

---

## If `docker pull` returns 403 (permission denied)
The VM's service account can't read the registry. Grant it read access (run from your machine,
replace `SA_EMAIL` with the VM's service account — find it with
`gcloud compute instances describe nvoiceai-vm --zone northamerica-northeast2-c --format='value(serviceAccounts.email)'`):
```bash
gcloud projects add-iam-policy-binding feisty-tempo-505518-b1 \
  --member="serviceAccount:SA_EMAIL" --role="roles/artifactregistry.reader"
```
Then re-run the `docker pull`.

---

## Rollback (removes ONLY the Streamlit — API never affected)
```bash
sudo docker stop invoice-streamlit && sudo docker rm invoice-streamlit
gcloud compute firewall-rules delete allow-streamlit-8501
```

---

## Updating later
Re-run Step 1 (`gcloud builds submit`), then on the VM:
```bash
sudo docker pull gcr.io/feisty-tempo-505518-b1/invoice-streamlit
sudo docker stop invoice-streamlit && sudo docker rm invoice-streamlit
sudo docker run -d --name invoice-streamlit --restart unless-stopped \
  -p 8501:8080 gcr.io/feisty-tempo-505518-b1/invoice-streamlit
```
The API container is untouched throughout.
```
```
