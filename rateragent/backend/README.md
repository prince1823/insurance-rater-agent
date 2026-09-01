# Backend — Insurance Rater Agent

FastAPI service: PDF → LLM extraction → deterministic rate resolution → cited trace,
persisted to Postgres + object storage. See the [top-level README](../README.md) for
architecture and deployment.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/analyze` | multipart `file` (PDF) → full structured result; persists a run. `?fixture=<name>` uses a bundled extraction fixture (no LLM key needed). |
| `GET` | `/runs` | run history (newest first) |
| `GET` | `/runs/{id}` | one run: summary + full `result` + `blob_key` |
| `GET` | `/runs/{id}/pdf` | the stored policy PDF (inline; the UI deep-links `#page=N`) |
| `GET` | `/health` | config/readiness probe |

## Output contract (`/analyze` response)

```jsonc
{
  "status": "resolved | unsupported | ambiguous",
  "insurer": "Reliance",
  "grid_file": "Reliance Broking Premier  FEB 26 Grid.xlsx",
  "policy_type": "comprehensive",
  "business_type": "renewal | rollover | new | unknown",
  "facts": { "<fact>": { "value": ..., "page": 2, "snippet": "...", "confidence": 0.95 }, ... },
  "rates": {
    "od": { "applicable": true,  "percent": 17.5, "basis": "OD premium", "note": "..." },
    "tp": { "applicable": true,  "percent": 0.0,  "basis": "TP / net premium", "note": "..." }
  },
  "commission_amounts_inr": { "od": 824.95, "tp": 0.0 },
  "confidence": { "level": "medium", "reason": "..." },
  "reason": "",                       // populated for unsupported / ambiguous or collapsed ambiguity
  "clarifying_question": null,
  "candidates": [],                   // alternative interpretations when ambiguous
  "citations": [ { "source": "...xlsx", "locator": "PRIVATE CAR COMP, SAOD & STP!C11",
                   "kind": "xlsx", "value": 22.5, "note": "" }, ... ],
  "trace": [ { "step": 1, "title": "...", "detail": "...", "citations": [ ... ] }, ... ],
  "extraction": { "model": "openai/gpt-4o-mini", "notes": [ ... ], "source_file": "policy.pdf" },
  "run_id": "…", "created_at": "…"
}
```

## Regenerating derived artefacts

```bash
python -m tools.compile_grids          # data/raters/* -> app/rulepacks/*.json
python -m tools.compile_grids --check  # non-zero exit if rulepacks drifted (also a pytest)
python -m tools.gen_traces             # -> ../docs/traces/*.{json,md}
```

## Adding a new insurer grid

1. Add a `compile_<insurer>()` to `tools/compile_grids.py` that emits a rulepack JSON with
   `sheet!cell` / `page` provenance for every value.
2. Add `app/resolver/<insurer>.py` with a `resolve(inp: ResolvedInput) -> ResolverResult`
   pipeline; append a `TraceStep` + `Citation` per lookup; raise `Unresolvable` instead of
   guessing.
3. Register it in `app/resolver/registry.py` (`_RESOLVERS` + `insurer_aliases` in the pack).
4. Add a hand-verified fixture under `tests/fixtures/` and a golden case in
   `tests/test_resolvers.py`.
