# 🧬 BioSynthetica — Autonomous Biology Research Engine

A professional React + FastAPI web platform for autonomous biological research:

- **Multi-source literature retrieval** — PubMed, PMC Open Access, Europe PMC, Crossref
- **Quote-grounded claim extraction** — every finding anchored to a verbatim quote
- **Cross-study contradiction detection** — finds where independent studies disagree
- **Mechanistic pathway synthesis** — multi-hop mechanism chains across studies
- **Falsifiable hypothesis formulation** — with experimental design specifications
- **Adversarial critic** — deterministic red-teaming of all synthesized claims
- **NCBI GEO loop closure** — links conflicting claims to real empirical datasets
- **Experimental data bridge** — upload your own CSV/XLSX to test replication

Built on the original Python research engine, rebuilt with a modern React frontend
and FastAPI backend. The legacy Streamlit app (`app.py`) is still included and works.

---

## Quick start

```bash
# 1. Install everything (Python + frontend deps)
bun run setup          # or: sh ./scripts/setup.sh

# 2. Add your Groq API key
#    Freebuff: Settings → Environment → add GROQ_API_KEY
#    Locally:  create a .env file with GROQ_API_KEY=gsk_...

# 3. Run
bun run dev            # or: sh ./scripts/dev.sh
# → http://localhost:8000
```

The FastAPI server serves both the REST/SSE API and the built React frontend
from a single port.

## Architecture

```
frontend/          React 18 + Vite + Tailwind (v4) SPA
  src/App.tsx      Investigation console (chat-style, live SSE progress)
  src/api.ts       Typed API client + SSE hook
api/
  server.py        FastAPI server wrapping the research engine
  requirements.txt Backend-layer deps (fastapi, uvicorn)
research_engine.py Core engine (unchanged): investigate() / run_agent()
ai_router.py       LLM cascade: Groq → NVIDIA NIM → Gemini
database.py        SQLite research knowledge store
scripts/           setup / dev / build / packaging helpers
electron/          Desktop shell (optional)
```

### API

| Endpoint | Description |
|---|---|
| `GET  /api/health` | Provider status |
| `POST /api/dataset` | Upload experimental CSV/XLSX |
| `POST /api/investigate` | Start a job (`mode`: `pipeline` or `agent`) |
| `GET  /api/jobs/:id` | Job snapshot (stage, progress) |
| `GET  /api/jobs/:id/events` | **SSE** live progress stream |
| `GET  /api/jobs/:id/result` | Report + dossier JSON |

## Downloadable desktop app (source-free)

The packaging flow compiles the entire Python engine into a **native binary**
with PyInstaller — no `.py` files ship in the bundle:

```bash
bun run package        # or: sh ./scripts/package_desktop.sh
# → dist-desktop/resources/BioSyntheticaServer   (compiled engine)
# → dist-desktop/resources/frontend/             (built React app)
```

To wrap it into native installers (`.exe` / `.dmg` / `.AppImage`):

```bash
cd electron
npm install
npm run dist
```

Electron launches the compiled server locally and opens the app in a native
window. Your `GROQ_API_KEY` stays in your machine's environment — it is never
baked into the bundle.

> **Note:** PyInstaller binaries are compiled, not obfuscated — they hide the
> source in normal distribution but are not cryptographically tamper-proof.
> For stronger protection, sell access to the hosted web app instead of
> distributing binaries.

## LLM configuration

The AI router cascades across providers (first available wins):

1. **Groq** — `GROQ_API_KEY` (recommended, free tier, fastest)
2. **NVIDIA NIM** — `NVIDIA_NIM_API_KEY`
3. **Gemini** — `GEMINI_API_KEY`

Optional: `NCBI_API_KEY` raises NCBI E-utilities rate limits.

## Legacy

`python research_engine.py "your question" --max-papers 6` — original CLI.
`streamlit run app.py` — original Streamlit chat UI.
