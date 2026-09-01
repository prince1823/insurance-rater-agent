# Insurance Rater Agent

An explainable agent that reads an Indian **motor-insurance policy PDF**, extracts the
facts that drive broker commission, looks up the applicable **Own-Damage (OD)** and
**Third-Party (TP)** brokerage percentages in the supplied insurer commission grids, and
returns the answer with **granular source citations** and an **ordered decision trace** —
or an evidence-backed refusal (`unsupported` / `ambiguous`) when the grids cannot support
an answer.

Built for the Vaatun "Solve to Join" challenge.

---

## Results for the four supplied policies

| Policy | Insurer | Cover | OD commission | TP commission | Status | Trace |
|---|---|---|---|---|---|---|
| `pvt-car-comprehensive-hdfc-ergo.pdf` | HDFC ERGO | Package | **15.0 %** on OD premium | 0 % (grid has no TP column) | `resolved` | [trace](docs/traces/pvt-car-comprehensive-hdfc-ergo.md) |
| `pvt-car-comprehensive-reliance.pdf` | Reliance | Package | **17.5 %** on OD premium (22.5 % base − 5 pts, < 1000 cc footnote) | 0 % (STP column) | `resolved` | [trace](docs/traces/pvt-car-comprehensive-reliance.md) |
| `pvt-car-satp-go-digit.pdf` | Go Digit | Stand-alone TP | _not applicable_ | **29.5 %** on TP/net premium | `resolved` | [trace](docs/traces/pvt-car-satp-go-digit.md) |
| `pvt-car-satp-tata-aig.pdf` | Tata AIG | Stand-alone TP | _not applicable_ | **38.0 %** on net premium | `resolved` | [trace](docs/traces/pvt-car-satp-tata-aig.md) |

Every number above is derived at runtime from the committed rulepacks — nothing is
hard-coded. Regenerate the traces with `cd backend && python -m tools.gen_traces`.

---

## Architecture

```
┌─────────────────┐   PDF upload    ┌────────────────────────┐  render pages   ┌────────────┐
│ React SPA        │ ──────────────▶ │ FastAPI backend        │ ──────────────▶ │ OpenRouter │
│ (Vite) on Vercel │ ◀────────────── │ (Docker) on Render     │  facts JSON     │ vision LLM │
└─────────────────┘  result + trace │                        │ ◀────────────── └────────────┘
                                     │  deterministic resolver │
                                     │  + JSON rulepacks       │
                                     └───────┬─────────┬───────┘
                                       runs  │         │  PDFs
                                   ┌──────────▼──┐  ┌───▼─────────────┐
                                   │ Supabase    │  │ Supabase        │
                                   │ Postgres    │  │ Storage bucket  │
                                   └─────────────┘  └─────────────────┘
```

**Two stages, one of which is deliberately *not* an LLM:**

1. **Extraction (LLM, `backend/app/extraction/`)** — PDF pages are rasterised with PyMuPDF
   and sent to an OpenRouter vision model under a strict JSON contract. Every fact returns
   with a **page number, a verbatim snippet, and a self-reported confidence**. Model is
   configurable (`OPENROUTER_MODEL`, default `openai/gpt-4o-mini`).

2. **Rate resolution (deterministic, `backend/app/resolver/`)** — a plain-Python pipeline,
   one module per insurer, that walks the compiled rulepack. Every lookup appends a
   `TraceStep` with the exact `Citation` (`file · sheet!cell` for XLSX, `file · page` for
   PDF) and the raw value read. A step that can't find a unique match **does not guess** —
   it returns `unsupported` (segment/zone/slab outside the grid) or `ambiguous` (a driver
   fact missing/weak, or ≥ 2 grid rows match) with the reason, the closest candidates, and
   an optional clarifying question.

### Grid rulepacks are precompiled

`backend/tools/compile_grids.py` reads the four source grids from `data/raters/` and emits
one normalized JSON per insurer into `backend/app/rulepacks/`, **retaining the sheet + cell
(or PDF page) of every value the resolver can read**. The runtime never opens an XLSX/PDF,
so rate resolution is fast, reproducible, and testable. `pytest` includes a check that the
committed rulepacks still match the source grids byte-for-byte.

### Why every grid needs its own resolver module

The four grids share no lookup shape:

| Insurer | Geography key | Segment axis | Rate axes | Notable overrides |
|---|---|---|---|---|
| **Reliance** | `RTO List` sheet → region-city + zone | fuel (Petrol/Bifuel vs Diesel/EV) | Zone × region → COMP / SA-OD / STP % | `< 1000 cc → −5 pts`; stand-alone ZD `−2.5 pts` |
| **Go Digit** | `4W  RTO` sheet → TP cluster | `Petrol<1000` / `Diesel>1500` … fuel+CC band + vehicle age | Cluster × segment × age → rate (fraction) | `All_India_Decline` cluster / "declined" note → unsupported |
| **Tata AIG** | RTO location / state → cluster-city column | Mini / Compact / Mid Size / MPV SUV / High End | (Segment × Business type × Fuel × Section × NCB × Add-on) → per-city column | SATP % on **net** premium; Package % on OD premium |
| **HDFC ERGO** | RTO → state → Zone-1 / Zone-2 | — (OD-premium slab instead) | Zone × slab × {Package/SAOD} × {Petrol/Non-petrol} × {NCB/N-NCB} | EV/Hybrid use petrol grid; no TP column ⇒ TP 0 % |

### Handling ambiguity (examples that ship as tests)

- **Missing RTO code** → `ambiguous`, asks for the RTO, never invents a zone.
- **Stand-alone TP policy** → OD reported as `not applicable`, never `0 %`.
- **Reliance < 1000 cc** → base rate reduced 5 points, footnote cited in the trace.
- **Tata AIG segment uncertain** (`Zen Estilo` → Mini _or_ Compact) → both looked up; if
  they yield the same rate the result is still `resolved` with the collapse noted;
  otherwise `ambiguous` with candidates.
- **HDFC ERGO fuel not printed** (Bolero Neo) → inferred with confidence ≤ 0.5, result
  downgraded to `medium` confidence and the assumption stated.
- **Unknown insurer** → `unsupported` (only Reliance / Go Digit / Tata AIG / HDFC ERGO).

---

## Repository layout

```
rateragent/
  backend/
    app/
      main.py               FastAPI: /analyze, /runs, /runs/{id}, /runs/{id}/pdf, /health
      pipeline.py           PDF bytes -> facts -> resolver -> output contract
      config.py             all config from env (12-factor)
      extraction/
        client.py           OpenRouter call + PDF->image rendering
        schema.py           PolicyFacts + per-field Evidence(page, snippet, confidence)
        normalize.py        fuel / RTO-code / business-type / policy-type canonicalisation
      resolver/
        base.py             Citation / TraceStep / RateComponent / ResolverResult / Unresolvable
        common.py           rulepack loader, fuzzy match, confidence scoring
        reliance.py  godigit.py  tataaig.py  hdfc_ergo.py   one pipeline per insurer
        segments.py          make/model -> segment candidates
        registry.py          insurer detection + dispatch
      rulepacks/*.json      compiled grids WITH cell provenance (committed)
      data/                 rto_state.json reference table
      storage/
        db.py                SQLAlchemy Run model (Postgres or sqlite fallback)
        blobs.py             Supabase Storage (or local dir fallback)
    tools/
      compile_grids.py       source grids -> rulepacks   (run offline; --check in CI/tests)
      gen_traces.py          rulepacks + fixtures -> docs/traces/*
    tests/                   resolver golden paths, edge cases, storage boundary, rulepack drift
      fixtures/*.json        hand-verified extraction payloads for the 4 samples
    Dockerfile  requirements.txt  .env.example
  frontend/                  Vite + React + TS SPA (upload, run history, trace + PDF viewer)
  data/                      the supplied bundle: sample-policies/ + raters/
  docs/traces/               structured output + human trace for each sample (committed)
  docker-compose.yml         local Postgres + backend
```

---

## Run it locally

### Backend (no external services needed — uses sqlite + local blob dir)

```bash
cd rateragent/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m tools.compile_grids        # writes app/rulepacks/*.json
uvicorn app.main:app --reload        # http://localhost:8000/docs
```

Analyse a bundled sample without an LLM key:

```bash
curl -X POST 'http://localhost:8000/analyze?fixture=pvt-car-satp-tata-aig' | jq .status,.rates
```

Analyse a real upload (needs `OPENROUTER_API_KEY` in `backend/.env`):

```bash
curl -X POST http://localhost:8000/analyze -F file=@some-policy.pdf | jq .
```

### Frontend

```bash
cd rateragent/frontend
npm install
echo 'VITE_API_BASE=http://localhost:8000' > .env.local
npm run dev                          # http://localhost:5173
```

### Everything in Docker

```bash
cd rateragent
OPENROUTER_API_KEY=sk-or-... docker compose up --build   # backend + Postgres on :8000
```

### Tests

```bash
cd rateragent/backend && pytest -q
```

Covers: the four sample policies resolve to the expected OD/TP with cited traces;
stand-alone-TP OD is `not applicable` (not 0 %); the Reliance sub-1000 cc footnote;
missing RTO / unknown insurer / out-of-grid RTO / unknown fuel / multi-column state →
correct refusal; weak extraction downgrades confidence; **storage boundary** — a persisted
run reloads identically from a brand-new engine (simulated redeploy); **rulepack drift** —
committed rulepacks still match the source grids.

---

## Deployment (Supabase + Render + Vercel — all free tier)

> **OpenRouter credits:** `gpt-4o-mini` vision calls are not free. Add a few dollars of
> credit at <https://openrouter.ai/settings/credits> or extraction returns `402 Payment
> Required`. The deterministic resolver and the `?fixture=` demo path work without it.

### 1. Supabase (persistent storage)

1. Create a project at <https://supabase.com>.
2. **Storage → New bucket** → name `policy-pdfs` (private is fine).
3. **Project Settings → Database → Connection string → URI** (port 5432) → this is
   `DATABASE_URL`.
4. **Project Settings → API** → copy `Project URL` (`SUPABASE_URL`) and the
   `service_role` key (`SUPABASE_SERVICE_KEY`).

No migration step is needed — the backend calls `Base.metadata.create_all` on startup and
creates the `runs` table.

### 2. Backend → Render (Docker)

1. Push this repo to GitHub.
2. Render → **New → Web Service** → connect the repo.
3. Settings:
   - **Root Directory:** `rateragent`
   - **Runtime:** Docker · **Dockerfile Path:** `backend/Dockerfile`
   - **Environment variables:** `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`,
     `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_BUCKET=policy-pdfs`,
     `CORS_ORIGINS=https://<your-vercel-app>.vercel.app`
4. Deploy. Health check: `GET https://<service>.onrender.com/health`.

### 3. Frontend → Vercel

1. Vercel → **New Project** → import the repo.
2. **Root Directory:** `rateragent/frontend` (framework auto-detects Vite).
3. **Environment variable:** `VITE_API_BASE = https://<service>.onrender.com`
4. Deploy. Update the backend's `CORS_ORIGINS` with the final Vercel URL and redeploy the
   backend.

---

## Storage & persistence — where uploads and analyses live

| Item | Stored in | Survives refresh / sign-out / restart / **redeploy**? |
|---|---|---|
| Uploaded policy PDF | Supabase **Storage** bucket `policy-pdfs`, key `runs/<run_id>.pdf` | ✅ — object storage, external to the container |
| Extracted facts + full structured output + decision trace | Supabase **Postgres** table `runs` (`facts_json`, `result_json`) | ✅ — managed database, external to the container |
| Run history list in the UI | fetched from `GET /runs` on every page load | ✅ — no client-side state; reload re-reads the DB |

The Render container keeps **nothing** analysis-related on local disk. There is no
authentication, so history is a single shared list (allowed by the challenge; if auth were
added the same rows would simply be scoped by a user id). If `DATABASE_URL` is unset the
app degrades to a local SQLite file + local blob dir — used only for tests and offline dev.

---

## Key design decisions

- **LLM only for extraction; rates are pure Python.** Grid resolution must be reproducible
  and explainable — an LLM never sees the grids.
- **Rulepacks carry provenance.** Every compiled value keeps its `sheet!cell` or `page`, so
  a citation is a lookup, not a reconstruction.
- **Refusal is a first-class outcome.** `Unresolvable(status, reason, clarifying_question,
  candidates)` is raised the moment a step can't be made deterministically.
- **Confidence is surfaced, not hidden.** Weak extraction (`confidence < 0.55` on a driver
  fact) or an inferred fuel downgrades the result to `medium`/`low` with the reason spelled
  out — a wrong number is worse than an honest "medium".
- **Configurable model.** `gpt-4o-mini` by default (as requested); raise to `openai/gpt-4o`
  or `google/gemini-2.0-flash-001` via env if extraction accuracy on dense scans is low.

## Assumptions

- Private-car line of business only (matches all four samples and the challenge scope);
  other LOBs → `unsupported`.
- Grids are frozen at the supplied versions.
- Reliance "PO will be 5% lesser" is read as **5 percentage points** (standard grid
  parlance); the alternative "5 % relative" reading is noted in the trace and limitations.
- HDFC ERGO grid publishes OD (Package/SAOD) commission only → TP commission is `0 %` for
  package policies, with the absence of a TP column cited.
- HDFC ERGO / Tata AIG business type: the sample schedules don't print a previous insurer,
  so business type is left `unknown`; it doesn't change the rate for those two grids in the
  sample cases (Reliance table is zone×fuel only; Tata AIG SATP is identical for Renewal /
  Rollover and the vehicle is too old to be Brand New).

## Known limitations & next steps

- **HDFC ERGO grid is hand-transcribed** from the scanned 2-page rate card (page citations
  retained). Direct table parsing was too unreliable; a `pdfplumber` parser with a
  transcription cross-check is the obvious follow-up.
- **Tata AIG RTO → cluster-city** relies on a curated state/city map; RTOs in multi-column
  states without a recognisable city → `ambiguous` (by design, but a fuller RTO table would
  resolve more).
- **Segment classification** uses a small curated model table + CC/body heuristics; rare
  models fall back to candidate lists. An insurer-published make/model sheet (Reliance has
  one) could be wired in per insurer.
- **Extraction quality** with `gpt-4o-mini` on dense multi-page scans is the main accuracy
  risk; mitigated by confidence gating + the configurable model, but a self-consistency /
  double-pass extraction and field-level re-prompting would help.
- **GWP-slab incremental rules** (Tata AIG) are portfolio-level, not single-policy, and are
  explicitly out of scope; noted where encountered.
- No auth, no rate-limiting, single shared history — fine for a review deployment.
