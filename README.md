# 🔍 Findora — AI-Powered Lost & Found Platform

> Reconnecting people with their belongings using computer vision, semantic text matching, and intelligent AI scoring.

[![Python](https://img.shields.io/badge/Python-3.10-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)](https://reactjs.org)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?style=flat-square&logo=supabase)](https://supabase.com)
[![Cloudinary](https://img.shields.io/badge/Cloudinary-Image%20Storage-3448C5?style=flat-square)](https://cloudinary.com)
[![Vercel](https://img.shields.io/badge/Frontend-Vercel-000000?style=flat-square&logo=vercel)](https://vercel.com)
[![Render](https://img.shields.io/badge/Backend-Render-46E3B7?style=flat-square)](https://render.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

**Live Demo →** [findora-ai-lost-found.vercel.app](https://findora-ai-lost-found.vercel.app)

---

## ✨ Features

- 📸 **Image-based reporting** — upload photos of lost or found items
- 🤖 **AI matching engine** — MobileNetV3 vision + Sentence Transformers text similarity
- 📍 **Location-aware search** — GPS-based proximity scoring
- 🎯 **High-confidence detection** — matches flagged at ≥80% confidence
- 📧 **Automated email alerts** — Brevo API notifies both parties on match
- 🔄 **Autonomous AI agent** — background worker continuously scans for new matches
- 💰 **Optional reward support** — reporters can offer rewards for returned items
- 🌐 **Production-deployed** — live on Vercel (frontend) + Render (backend)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FINDORA SYSTEM                          │
└──────────────┬──────────────────────────┬───────────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────┐      ┌───────────────────────────┐
│   FRONTEND           │      │   BACKEND (Render)        │
│   React 18           │◄────►│   FastAPI + Uvicorn       │
│   Tailwind CSS        │      │   Python 3.10             │
│   Lucide Icons        │      │   autonomous agent.py     │
│   Axios               │      └───────────┬───────────────┘
│   Vercel CDN          │                  │
└──────────────────────┘       ┌───────────▼───────────────┐
                               │   AI ENGINE               │
                               │   MobileNetV3 (vision)    │
                               │   all-MiniLM-L6-v2 (text) │
                               │   Isolation Forest (ML)   │
                               │   Cosine similarity       │
                               │   Location scoring        │
                               └───────────┬───────────────┘
                                           │
              ┌────────────────────────────┼──────────────────┐
              │                            │                  │
              ▼                            ▼                  ▼
  ┌──────────────────┐        ┌─────────────────┐  ┌─────────────────┐
  │  Supabase        │        │  Cloudinary     │  │  Brevo API      │
  │  PostgreSQL DB   │        │  Image Storage  │  │  Email Alerts   │
  │  (Tokyo region)  │        │  CDN delivery   │  │  300/day free   │
  └──────────────────┘        └─────────────────┘  └─────────────────┘
```

---

## 🛠️ Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Framework | FastAPI 0.104 + Uvicorn |
| Language | Python 3.10.13 |
| Database | Supabase (PostgreSQL via psycopg2, IPv4 pooler) |
| Image Storage | Cloudinary (upload + CDN URL serving) |
| Vision AI | MobileNetV3Small (TensorFlow/Keras — `.keras` format) |
| Text AI | Sentence Transformers `all-MiniLM-L6-v2` |
| Email | Brevo HTTP API (300 emails/day, no domain needed) |
| Deployment | Render (Python 3 free tier, persistent disk `/data`) |

### Frontend
| Layer | Technology |
|---|---|
| Framework | React 18 |
| Styling | Tailwind CSS |
| Icons | Lucide React |
| HTTP client | Axios |
| Deployment | Vercel (static build, CDN) |

### DevOps
| Tool | Usage |
|---|---|
| GitHub Actions | CI on every push/PR — backend pytest suite + frontend production build |
| Vercel | Auto-deploy frontend on push to `main` |
| Render | Auto-deploy backend on push to `main` |

---

## 🧠 AI / ML Overview

### Vision Matching — MobileNetV3
- Pre-trained MobileNetV3Small backbone with L2 normalisation layer
- Extracts a compact feature vector per image
- Supports both local file paths and **Cloudinary `https://` URLs** (downloads to temp file)
- Falls back to rebuilding the model if no saved `.keras` file is found

### Text Matching — Sentence Transformers
- `all-MiniLM-L6-v2` encodes item title + description into a dense embedding
- L2-normalised before cosine similarity scoring

### Confidence Scoring Formula
```
confidence = (image_similarity  × 0.40)
           + (text_similarity   × 0.35)
           + (location_score    × 0.15)
           + (temporal_score    × 0.10)
           + (category_boost    +0.10 same category / −0.05 different)
```
- The final score is clamped to a maximum of **95%**
- Matches stored in DB at ≥ **60%** confidence
- Email notifications triggered at ≥ **80%** confidence

### Autonomous AI Agent (`agent.py`)
- Runs every **30 seconds** in the background
- Observes items missing extracted features → extracts them
- Batch-matches new items against all opposite-type active items (top 5)
- Calls `notify_match()` → sends Brevo emails to both lost & found parties

---

## 📦 Local Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Supabase project (for `DATABASE_URL`)
- Cloudinary account (for image storage)
- Brevo API key (for email notifications)

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # fill in your keys
python main.py
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env           # set REACT_APP_API_URL
npm start
```

### Environment Variables

Create a `.env` file in `backend/` — never commit this file.

#### Backend
| Variable | Where to get it |
|---|---|
| `DATABASE_URL` | Supabase → Project Settings → Database → Connection string (IPv4 pooler) |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary → Dashboard |
| `CLOUDINARY_API_KEY` | Cloudinary → API Keys |
| `CLOUDINARY_API_SECRET` | Cloudinary → API Keys |
| `BREVO_API_KEY` | Brevo → SMTP & API → API Keys |
| `FROM_EMAIL` | Your sender email address |
| `FROM_NAME` | Display name (e.g. `Findora`) |
| `GMAIL_ADDRESS` | Optional — used as the Reply-To address on match emails |
| `PORT` | Optional — local dev port (default `8000`; Render sets it automatically) |
| `LLM_API_KEY` | Optional — free key for the AI Assistant (Groq or Gemini, see below). Without it `/api/agent/chat` returns 503 and the rest of the app is unaffected |
| `LLM_BASE_URL` | Optional — OpenAI-compatible endpoint (default `https://api.groq.com/openai/v1`) |
| `LLM_MODEL` | Optional — model name (default `openai/gpt-oss-120b`) |

Templates: [`backend/.env.example`](backend/.env.example) and [`frontend/.env.example`](frontend/.env.example).

#### Frontend
| Variable | Description |
|---|---|
| `REACT_APP_API_URL` | Your Render backend service URL |
| `REACT_APP_SUPABASE_URL` | Supabase → Project Settings → API (used for sign-in) |
| `REACT_APP_SUPABASE_ANON_KEY` | Supabase → Project Settings → API (anon/public key) |

> All secrets are managed via Render and Vercel environment variable dashboards in production.

---

## 🤖 AI Assistant (chat agent)

A tool-calling chat agent, written from scratch (plain `requests`, no LangChain). Users ask in plain
English — *"I lost a black wallet near the library"* — and the model decides which tools to call.

```
Browser (AgentChat.js) ──POST /api/agent/chat──► main.py ──► chat_agent/agent.py  (loop, max 5 steps)
                                                                 │        ▲
                                                   LLM (any OpenAI-compatible API)
                                                                 ▼        │
                                                       chat_agent/tools.py  ──► database
```

| Tool | What it does |
|---|---|
| `search_items` | Keyword search over lost/found reports (public fields only) |
| `get_my_items` | Lists the signed-in user's own reports |
| `get_item_matches` | AI matches for one of the user's own items (ownership checked) |
| `get_stats` | Platform totals |
| `draft_report` | Prepares a report draft; the UI pre-fills the Report form. **Never submits anything** |

**Privacy by design:** contact info, user IDs and embeddings are never returned to the model
(whitelisted `public_item`); chat history from the browser is sanitised (only `user`/`assistant`
roles accepted); item text is treated as data, not instructions; per-IP rate limit (20 requests / 10 min);
provider errors are not leaked to the browser.

**Enable it (free):**
1. Get a free key from [Groq](https://console.groq.com/keys) *or* [Google AI Studio](https://aistudio.google.com/apikey).
2. Set `LLM_API_KEY` (and for Gemini also `LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai`,
   `LLM_MODEL=gemini-2.0-flash`) in `backend/.env` locally, or in the Render dashboard.
3. Open the **Assistant** tab in the app.

> Free tiers have rate limits, and Gemini's free tier may use prompts to improve Google products — don't use it with data you consider private.

**Known limitations (v1):** `user_id` is supplied by the client — verify the Supabase JWT server-side before relying on it for
anything sensitive; search is lexical (could reuse the MiniLM embeddings later).

---

## 🔁 How It Works

```
1. User reports a lost or found item
         │
         ▼
2. Image uploaded → Cloudinary CDN
   Item metadata → Supabase (PostgreSQL)
         │
         ▼
3. AI Agent wakes every 30s
   → MobileNetV3 extracts image features
   → MiniLM extracts text embedding
   → Features stored back to Supabase
         │
         ▼
4. Batch match against opposite-type items
   → Cosine similarity (vision + text)
   → Location proximity score
   → Weighted confidence score computed
         │
         ▼
5. Confidence ≥ 60%  → stored as pending match
   Confidence ≥ 80%  → Brevo email sent to BOTH parties
         │
         ▼
6. Users receive match alert email with
   item details, confidence score, and contact info
```

---

## 📁 Project Structure

```
findora-ai-lost-found/
├── backend/
│   ├── main.py                  ← FastAPI app + all routes
│   ├── database.py              ← Supabase PostgreSQL (psycopg2)
│   ├── models.py                ← Pydantic request/response models
│   ├── notifications.py         ← Brevo email engine
│   ├── chat_agent/
│   │   ├── agent.py             ← Tool-calling loop, prompt, history sanitising
│   │   ├── tools.py             ← Tools + public-field whitelist
│   │   ├── llm.py               ← OpenAI-compatible client (requests)
│   │   └── ratelimit.py         ← Sliding-window limiter
│   ├── ai/
│   │   ├── engine.py            ← MobileNetV3 + MiniLM AI engine
│   │   └── agent.py             ← Autonomous AI matching agent
│   ├── tests/                   ← pytest suite (runs offline, no DB or models needed)
│   ├── requirements.txt         ← full runtime dependencies
│   ├── requirements-test.txt    ← lightweight dependencies used by CI
│   ├── pytest.ini
│   ├── .env.example
│   └── runtime.txt              ← python-3.10.13
├── frontend/
│   ├── src/
│   │   ├── App.js               ← Main React app (report, browse, matches)
│   │   ├── AgentChat.js         ← AI Assistant chat tab
│   │   ├── AuthPage.js          ← Email / Google sign-in + guest mode
│   │   ├── AuthContext.js       ← Supabase auth state
│   │   ├── DashboardPage.js     ← User dashboard
│   │   ├── SplashScreen.js
│   │   ├── supabaseClient.js
│   │   ├── index.js
│   │   └── index.css
│   ├── public/
│   │   └── index.html
│   ├── config.js                ← API URL from env
│   ├── .env.example
│   └── package.json
├── .github/
│   └── workflows/ci.yml         ← backend tests + frontend build
├── supabase_schema.sql          ← profiles + notifications tables
├── render.yaml                  ← Render deployment config (backend)
└── vercel.json                  ← Vercel frontend deployment
```

---

## 🧪 Testing

The backend has a pytest suite that runs fully offline: the database is stubbed,
no email is sent, and the AI models are never loaded, so it needs no TensorFlow
or sentence-transformers install.

```bash
cd backend
pip install -r requirements-test.txt
python -m pytest tests -q
```

| File | Covers |
|---|---|
| `test_models.py` | Category / item-type / status validators, request-model validation |
| `test_keyword_matching.py` | Fast keyword matcher (exact title → 0.92, 0.90 cap, category bonus) |
| `test_engine_scoring.py` | Confidence formula, location decay, time decay, 95% cap, thresholds |
| `test_notifications.py` | Contact parsing, email validation, match-alert text, send guards |
| `test_api.py` | `/ping`, `/health`, report validation + success path, items, matches, stats |
| `test_chat_agent_tools.py` | Tools, field whitelist, ownership checks, draft validation |
| `test_chat_agent_loop.py` | Agent loop with a scripted fake LLM, history sanitising, step limit |
| `test_chat_agent_llm.py` | LLM client errors (missing key, 429, malformed response) |
| `test_chat_agent_api.py` | `/api/agent/chat` status codes (503/429/400/502) and no error leakage |
| `test_chat_agent_wire.py` | Real HTTP round-trip against a mock OpenAI-compatible server |
| `test_ratelimit.py` | Sliding-window limiter |

GitHub Actions runs this suite plus a production build of the React app on every push and pull request.

---

## 🚀 Deployment

| Service | URL | Platform |
|---|---|---|
| Frontend | [findora-ai-lost-found.vercel.app](https://findora-ai-lost-found.vercel.app) | Vercel |
| Backend API | [findora-ai-lost-found-1.onrender.com](https://findora-ai-lost-found-1.onrender.com) | Render |
| Database | Supabase (ap-northeast-1, Tokyo) | Supabase |
| Images | Cloudinary CDN | Cloudinary |

> **Note:** The Render free tier spins down after inactivity. First request may take ~50s to cold start.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 👨‍💻 Author

**Deepak Roshan A**
AI / ML • Computer Vision • Full-Stack Development

[![LinkedIn](https://img.shields.io/badge/LinkedIn-deepakroshan--adr-blue?style=flat-square&logo=linkedin)](https://linkedin.com/in/deepakroshan-adr)
[![GitHub](https://img.shields.io/badge/GitHub-deepakroshan11-black?style=flat-square&logo=github)](https://github.com/deepakroshan11)

---

*Built to reconnect people with what matters to them — powered by AI.*
