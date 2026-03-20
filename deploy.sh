#!/usr/bin/env bash
# deploy.sh — Build and deploy the Text Summarization Agent to Cloud Run
# Usage: ./deploy.sh [PROJECT_ID] [REGION] [GOOGLE_API_KEY]
# All args fall back to env vars of the same name.

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
PROJECT_ID="${1:-${PROJECT_ID:?'Set PROJECT_ID env var or pass as arg 1'}}"
REGION="${2:-${REGION:-us-central1}}"
GOOGLE_API_KEY="${3:-${GOOGLE_API_KEY:?'Set GOOGLE_API_KEY env var or pass as arg 3'}}"

SERVICE_NAME="text-summarization-agent"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

echo "==========================================="
echo "  Deploying ${SERVICE_NAME}"
echo "  Project : ${PROJECT_ID}"
echo "  Region  : ${REGION}"
echo "  Image   : ${IMAGE}"
echo "==========================================="

# ── 1. Authenticate / set project ────────────────────────────────────────────
gcloud config set project "${PROJECT_ID}"

# ── 2. Enable required APIs ───────────────────────────────────────────────────
echo "→ Enabling GCP APIs …"
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  secretmanager.googleapis.com \
  --quiet

# ── 3. Store API key in Secret Manager ───────────────────────────────────────
echo "→ Storing API key in Secret Manager …"
if gcloud secrets describe google-api-key --project="${PROJECT_ID}" &>/dev/null; then
  echo "   Secret already exists — adding new version."
  echo -n "${GOOGLE_API_KEY}" | gcloud secrets versions add google-api-key \
    --data-file=- --project="${PROJECT_ID}"
else
  echo -n "${GOOGLE_API_KEY}" | gcloud secrets create google-api-key \
    --data-file=- --replication-policy=automatic --project="${PROJECT_ID}"
fi

# ── 4. Build & push Docker image ─────────────────────────────────────────────
echo "→ Building Docker image …"
docker build -t "${IMAGE}" .

echo "→ Pushing image to GCR …"
docker push "${IMAGE}"

# ── 5. Deploy to Cloud Run ────────────────────────────────────────────────────
echo "→ Deploying to Cloud Run …"
gcloud run deploy "${SERVICE_NAME}" \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --port=8080 \
  --set-env-vars="GEMINI_MODEL=gemini-2.0-flash" \
  --update-secrets="GOOGLE_API_KEY=google-api-key:latest" \
  --quiet

# ── 6. Print service URL ───────────────────────────────────────────────────────
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" \
  --format="value(status.url)")

echo ""
echo "==========================================="
echo "  ✅  Deployment complete!"
echo "  Service URL: ${SERVICE_URL}"
echo "==========================================="
echo ""
echo "Test it:"
echo "  curl ${SERVICE_URL}/"
echo ""
echo "  curl -X POST ${SERVICE_URL}/summarize \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"text\": \"Paste your text here.\"}'"
