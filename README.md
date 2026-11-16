# Page Chat Assistant

A browser extension (Chrome / Edge / Safari) that reads the page you are on and lets you chat with it.
Answers are grounded in the page **and** your company policy documents (RAG), and pass through guardrails.

```
Browser extension (popup)  ──HTTPS──►  FastAPI backend ──► LangGraph agent
                                           │                  ├─ input guardrails
  reads page text                          │                  ├─ token cache lookup      (PostgreSQL)
  sends question + page                    │                  ├─ RAG: page chunks + policy chunks (Qdrant)
                                           │                  ├─ auto model router (small / large)
                                           │                  ├─ LLM (free: Groq / Gemini / Ollama)
                                           │                  ├─ output guardrails + policy verifier
                                           │                  └─ cache store
                                      PostgreSQL · Qdrant
```

## 1. Folder structure

```
page-chat-assistant/
├── docker-compose.yml          # postgres + qdrant + backend in one command
├── .env.example                # copy to .env and edit
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI entry point
│   │   ├── core/               # config, database, container (startup objects), utils
│   │   ├── models/             # SQLAlchemy tables      (chat, document, cache)
│   │   ├── schemas/            # Pydantic request/response models
│   │   ├── repositories/       # ONLY layer touching DB/Qdrant (repository pattern)
│   │   ├── services/           # business logic: guardrails, router, cache, RAG, LLM client, prompts
│   │   ├── agents/             # LangGraph workflow (graph.py = the whole request lifecycle)
│   │   └── api/                # HTTP routes + dependencies (auth, wiring)
│   ├── scripts/ingest_policies.py   # bulk-load policy files
│   ├── policies/               # put your policy PDFs/DOCX/TXT/MD here
│   ├── tests/                  # 14 tests, run without DB / LLM
│   ├── Dockerfile, requirements.txt
└── extension/                  # Manifest V3 extension (plain JS, no build step)
    ├── manifest.json, popup.html, css/popup.css
    └── js/  popup.js (controller) · pageReader.js · apiClient.js · storage.js · ui.js
```

Layering rule: `api → services → repositories → DB/Qdrant`. Services never write SQL.

## 2. How your 14 requirements are met

| # | Requirement | Where |
|---|---|---|
| 1,5 | Easy to understand | Small files, one job each, comments everywhere |
| 2 | Repository pattern | `backend/app/repositories/`, `extension/js/storage.js` |
| 3 | Optimal tokens | Only top-K page chunks sent; short history; short prompts; `max_tokens` caps; free local embeddings; 5-token verifier |
| 4 | Comments | Every file/function |
| 6 | Token caching | `services/cache_service.py` → Postgres `response_cache` (key = question + page hash + policy version + last turn, TTL 24h). Cache auto-invalidates when policies change |
| 7 | Free LLM | Groq free tier by default; Ollama / Gemini / OpenRouter by changing 4 `.env` lines |
| 8 | RAG with policies | `document_service.py` + `vector_repository.py` (Qdrant); retrieved on every question and used to verify the answer |
| 9 | Guardrails | `services/guardrails.py` (input, page-injection, output PII/leak/unsafe) + `verifier.py` (policy consistency) |
| 10 | Auto model switching | `services/model_router.py` (zero-token heuristic) + automatic escalation small→large if output fails a check |
| 11,12 | Python stack | FastAPI, Pydantic, SQLAlchemy (async), PostgreSQL, Qdrant, LangGraph, fastembed, openai-client |
| 13 | Backend architecture | Sections 1 and 3 |
| 14 | File structure | Section 1 |

## 3. Request lifecycle (LangGraph, `agents/graph.py`)

1. **input_guard** – reject empty/too long/prompt-injection; strip malicious lines from the page.
2. **cache_lookup** – hit ⇒ answer returned with **0 tokens**.
3. **retrieve** – embed question once; select relevant page chunks (long pages) + top policy chunks from Qdrant.
4. **route** – score the question: simple ⇒ small model, complex ⇒ large model.
5. **generate** – call the LLM with a minimal prompt.
6. **output_guard** – PII/secret redaction, leak/unsafe checks, then policy-consistency verifier. If the **small** model fails, retry **once** with the large model; if still failing, return a safe fallback.
7. **finalize** – store good answers in the cache.

---

## 4. Step-by-step: run it

### Step 0 – Install prerequisites
* **Docker Desktop** (https://www.docker.com/products/docker-desktop) – easiest path.
* A browser: Chrome or Edge (Safari needs a Mac, see Step 6).
* (Only for manual run / tests) **Python 3.11+**.

### Step 1 – Get a FREE LLM key
1. Go to https://console.groq.com/keys → sign up → **Create API key**.
2. Copy the key. (No credit card needed. Free tier has rate limits – the cache and small-model routing help you stay within them.)

*Prefer fully offline?* Install Ollama (https://ollama.com), run `ollama pull llama3.2:3b` and `ollama pull llama3.1:8b`, then use the Ollama values in `.env.example`. If the backend runs in Docker, use `LLM_BASE_URL=http://host.docker.internal:11434/v1`.

### Step 2 – Configure
```bash
cd page-chat-assistant
cp .env.example .env          # Windows PowerShell: copy .env.example .env
```
Open `.env` and set:
* `LLM_API_KEY=` your Groq key
* `API_KEY=` any long random string (you will paste the same value into the extension)

### Step 3 – Start everything (Docker)
```bash
docker compose up -d --build
docker compose logs -f backend      # wait for "Startup complete", then Ctrl+C
```
Open http://localhost:8000/health → `{"status":"ok"}` and http://localhost:8000/docs (Swagger UI).
The first build downloads the embedding model (~130 MB) – this takes a few minutes once.

### Step 4 – Load your company policy documents (RAG)
**Option A – bulk (recommended):** copy files (`.pdf .docx .txt .md`) into `backend/policies/`, then
```bash
docker compose exec backend python -m scripts.ingest_policies policies
```
A sample `sample_leave_policy.md` is included so you can test immediately (delete it later from the API: `DELETE /api/v1/documents/{id}`).

**Option B – via API:** open http://localhost:8000/docs → click **Authorize** is not needed; instead use `POST /api/v1/documents`, add header `X-API-Key`, choose a file → Execute.
Or with curl:
```bash
curl -X POST http://localhost:8000/api/v1/documents -H "X-API-Key: YOUR_API_KEY" -F "file=@my_policy.pdf"
```
Re-uploading identical content is ignored; changing/adding/removing a document automatically invalidates the answer cache.

### Step 5 – Install the extension (Chrome / Edge)
1. Chrome: open `chrome://extensions`  ·  Edge: open `edge://extensions`
2. Turn on **Developer mode**.
3. Click **Load unpacked** → select the `extension/` folder.
4. Pin the extension (puzzle icon → pin).
5. Open any website, click the extension icon. Click **⚙**, enter Backend URL `http://localhost:8000` and your `API_KEY`, press **Save**.
6. Ask a question, e.g. on any article: *"Summarize this page"*. Try *"How many days of annual leave do employees get?"* to see policy sources `[P1]`.

Under each answer you see: model used, tokens, `⚡ cached` on repeats, guardrail flags, and expandable policy sources.

### Step 6 – Safari (macOS only)
Requires macOS + Xcode (free from the App Store).
```bash
xcrun safari-web-extension-converter ./extension --app-name "Page Chat Assistant" --macos-only
```
Xcode opens → press ▶ Run → in Safari: **Settings → Extensions** → enable *Page Chat Assistant* → allow it on websites. For Safari the backend must be reachable from the Mac (localhost works).

### Step 7 – Run tests (optional)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -q                                              # 14 passed
```

### Manual run without Docker for the backend (optional)
```bash
docker compose up -d postgres qdrant
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env        # edit LLM_API_KEY and API_KEY
uvicorn app.main:app --reload --port 8000
```

## 5. Tuning knobs (`.env`)
| Setting | Effect |
|---|---|
| `COMPLEXITY_THRESHOLD` | lower ⇒ more queries use the large model |
| `PAGE_TOP_K`, `POLICY_TOP_K` | more context vs fewer tokens |
| `POLICY_MIN_SCORE` | ignore weak policy matches |
| `ENABLE_VERIFIER=false` | skip the extra (cheap) policy-consistency call |
| `CACHE_TTL_SECONDS` | how long cached answers live |
| `REDACT_PII=false` | stop redacting emails/phones in answers |

## 6. Production checklist (honest notes)
* Put the backend behind **HTTPS** (Caddy / Nginx / cloud load balancer). Then add the HTTPS host to the extension's `host_permissions` in `manifest.json` (or users grant it when prompted, `optional_host_permissions` is already set).
* Replace the shared `API_KEY` with SSO/OAuth (e.g. company IdP) – edit `api/deps.py::require_api_key`.
* Change the Postgres password in `docker-compose.yml`; don't expose ports 5432/6333 publicly.
* Add Alembic migrations when you change tables (currently `create_all` at startup).
* Add rate limiting (e.g. `slowapi`) and log shipping/monitoring for your environment.
* The page text is sent to your backend and then to the LLM provider. Free-tier providers may use data for improvement – for confidential pages use **Ollama (local)** or a provider with a no-training agreement.
* Guardrails are rule-based + a small-model check: strong baseline, not a guarantee. Review them against your compliance needs.

## 7. Troubleshooting
| Problem | Fix |
|---|---|
| "Cannot reach backend" | `docker compose ps`; open http://localhost:8000/health; check ⚙ URL |
| "Wrong API key" | `API_KEY` in `.env` must equal the key in ⚙ (restart: `docker compose up -d`) |
| "Page can't be read" | Browser-internal pages (`chrome://`, web store) are blocked by the browser |
| 429 / rate limit errors | Free-tier limit: wait a minute, or use Ollama |
| Backend slow on first start | Embedding model loading; wait for "Startup complete" |
| Changed `.env` | `docker compose up -d` again |



##############Downloading the embedding model##############
python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5', cache_dir='.models'); print('model ready')"