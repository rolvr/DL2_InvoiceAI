# deploy/ — isolated Streamlit deployment (Parts 4 & 5)

Self-contained container + cloud-deploy setup for the **Streamlit Showcase**, kept separate so it
never disturbs the existing app/API in the repo.

| File | Purpose |
|---|---|
| `Dockerfile` | Builds the Showcase image (app + src + config + weights + EasyOCR baked in). Build from repo root: `docker build -f deploy/Dockerfile -t invoice-streamlit .` |
| `cloudbuild.yaml` | Cloud Build config so GCP builds this Dockerfile from the repo-root context. |
| `DEPLOY_GCP.md` | Step-by-step GCP deploy — Cloud Run (recommended) or Compute Engine VM. Uses new, uniquely named resources so it won't touch an existing deployment. |

Part 3 (REST API + curl/Postman/Python clients) already exists in the main repo (`app/api.py`,
`clients/`). This bundle deploys the Streamlit app, which is the visual client.
