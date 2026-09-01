# Frontend — Insurance Rater Agent

Vite + React + TypeScript single-page app.

- **Upload** a policy PDF (drag-drop or click) or run one of the four bundled samples.
- **Run history** (left) is loaded from `GET /runs` on every mount, so it survives refresh,
  reopen, and backend redeploys.
- **Result view**: status badge, OD/TP rate cards (stand-alone TP shows "not applicable"),
  extracted-facts table with page deep-links, the ordered decision trace with per-step
  citations, and an inline PDF viewer that jumps to a cited page (`#page=N`).

## Dev

```bash
npm install
echo 'VITE_API_BASE=http://localhost:8000' > .env.local
npm run dev
```

## Build / deploy

`npm run build` → `dist/`. On Vercel set **Root Directory** `rateragent/frontend` and env
var `VITE_API_BASE` to the Render backend URL. `vercel.json` handles the SPA rewrite.
