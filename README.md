# 🤖 Text Summarization Agent — ADK + Gemini on Cloud Run

A production-ready AI agent built with **Google Agent Development Kit (ADK)** and **Gemini**, deployed on **Cloud Run**. Accepts raw text via HTTP and returns a structured JSON summary.

---

## Architecture

```
HTTP Client
    │
    ▼
Cloud Run (FastAPI)
    │
    ├── GET  /            → Health check
    ├── POST /summarize   → Summarization agent
    └── POST /chat        → Free-form agent chat
         │
         ▼
    Google ADK Runner
         │
         ▼
    Gemini 2.0 Flash  ←── Google AI / Vertex AI
```

### Key components

| File | Purpose |
|------|---------|
| `agent.py` | ADK `Agent` definition with tool + system prompt |
| `main.py` | FastAPI app, lifespan wiring, endpoint handlers |
| `Dockerfile` | Multi-stage build optimised for Cloud Run |
| `deploy.sh` | One-command deploy script |
| `cloudbuild.yaml` | CI/CD via Cloud Build |
| `tests.py` | Unit + integration tests |

---

## Quick start (local)

### 1 — Prerequisites

- Python 3.12+
- A **Google AI Studio** API key → https://aistudio.google.com/app/apikey

### 2 — Install

```bash
git clone <your-repo-url>
cd gemini-adk-agent

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 3 — Configure

```bash
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY=<your key>
```

### 4 — Run

```bash
python main.py
# Server starts at http://localhost:8080
```

### 5 — Test

```bash
# Health check
curl http://localhost:8080/

# Summarise text
curl -X POST http://localhost:8080/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Artificial intelligence is the simulation of human intelligence
             processes by computer systems. These processes include learning,
             reasoning, and self-correction. AI is used in a wide range of
             fields including healthcare, finance, and transportation."
  }'
```

**Example response:**

```json
{
  "summary": "Artificial intelligence simulates human cognitive processes such as learning and reasoning using computer systems. It is now widely applied across diverse sectors including healthcare, finance, and transportation.",
  "key_points": [
    "AI simulates human intelligence processes",
    "Core capabilities include learning, reasoning, and self-correction",
    "Applied across healthcare, finance, and transportation"
  ],
  "word_count": 42,
  "session_id": "session_1718000000000",
  "elapsed_ms": 1230.45
}
```

---

## Deploy to Cloud Run

### Option A — Shell script (recommended for first deploy)

```bash
chmod +x deploy.sh

./deploy.sh \
  your-gcp-project-id \
  us-central1 \
  your-google-api-key
```

The script will:
1. Enable required GCP APIs
2. Store your API key in **Secret Manager**
3. Build and push the Docker image to **Container Registry**
4. Deploy to **Cloud Run** with `--allow-unauthenticated`
5. Print the live service URL

### Option B — Manual steps

```bash
# 1. Set project
gcloud config set project YOUR_PROJECT_ID

# 2. Enable APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  containerregistry.googleapis.com secretmanager.googleapis.com

# 3. Store API key
echo -n "YOUR_API_KEY" | gcloud secrets create google-api-key \
  --data-file=- --replication-policy=automatic

# 4. Build & push image
IMAGE="gcr.io/YOUR_PROJECT_ID/text-summarization-agent:latest"
docker build -t $IMAGE .
docker push $IMAGE

# 5. Deploy
gcloud run deploy text-summarization-agent \
  --image=$IMAGE \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=512Mi \
  --port=8080 \
  --set-env-vars="GEMINI_MODEL=gemini-2.0-flash" \
  --update-secrets="GOOGLE_API_KEY=google-api-key:latest"
```

### Option C — Cloud Build CI/CD

```bash
gcloud builds submit --config cloudbuild.yaml \
  --substitutions="_REGION=us-central1"
```

---

## API Reference

### `GET /`

Health check.

**Response 200:**
```json
{ "status": "ok", "service": "text-summarization-agent", "model": "gemini-2.0-flash" }
```

---

### `POST /summarize`

Run the summarization agent.

**Request body:**
```json
{
  "text": "string (min 10 chars, required)",
  "session_id": "string (optional)"
}
```

**Response 200:**
```json
{
  "summary": "string",
  "key_points": ["string", "..."],
  "word_count": 0,
  "session_id": "string",
  "elapsed_ms": 0.0
}
```

---

### `POST /chat`

Free-form interaction with the agent.

**Request body:**
```json
{
  "message": "string (required)",
  "session_id": "string (optional)"
}
```

**Response 200:**
```json
{
  "response": "string",
  "session_id": "string",
  "elapsed_ms": 0.0
}
```

---

## Running tests

```bash
# Unit tests only (no API key needed)
SKIP_INTEGRATION=1 pytest tests.py -v

# All tests (requires GOOGLE_API_KEY)
pytest tests.py -v
```

---

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_API_KEY` | ✅ | — | Google AI / Vertex AI key |
| `GEMINI_MODEL` | ❌ | `gemini-2.0-flash` | Gemini model name |
| `PORT` | ❌ | `8080` | Server port (set by Cloud Run) |

---

## Cost estimate

With Cloud Run's scale-to-zero and Gemini 2.0 Flash pricing this agent costs **~$0** at rest and is very cheap under moderate load (Flash is one of the most cost-efficient Gemini models).

---

## License

MIT
