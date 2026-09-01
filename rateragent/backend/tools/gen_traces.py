"""Regenerate docs/traces/<policy>.json + .md for every bundled fixture."""
import json, pathlib
from app.extraction.client import facts_from_payload
from app.pipeline import build_output

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
FIX = ROOT / "backend" / "tests" / "fixtures"
OUT = ROOT / "docs" / "traces"
OUT.mkdir(parents=True, exist_ok=True)

def md(name, out):
    L = [f"# Decision trace — `{name}.pdf`", ""]
    L += [f"- **Status:** `{out['status']}`",
          f"- **Insurer:** {out['insurer']}  (grid: `{out['grid_file']}`)",
          f"- **Policy type:** {out['policy_type']}  ·  **Business type:** {out['business_type']}",
          f"- **OD commission:** " + (f"{out['rates']['od']['percent']}% on {out['rates']['od']['basis']}" if out['rates']['od']['applicable'] else "_not applicable_"),
          f"- **TP commission:** " + (f"{out['rates']['tp']['percent']}% on {out['rates']['tp']['basis']}" if out['rates']['tp']['applicable'] else "_not applicable_"),
          f"- **Confidence:** {out['confidence']['level']} — {out['confidence']['reason']}", ""]
    if out["reason"]:
        L += [f"> {out['reason']}", ""]
    if out["clarifying_question"]:
        L += [f"**Clarifying question:** {out['clarifying_question']}", ""]
    L += ["## Extracted facts", "", "| Fact | Value | Page | Confidence |", "|---|---|---|---|"]
    f = out["facts"]
    for k, v in f.items():
        if k == "premium_breakup":
            continue
        val = v.get("value"); pg = v.get("page", ""); cf = v.get("confidence", "")
        L.append(f"| {v.get('field', k)} | {val} | {pg or ''} | {cf if cf!='' else ''} |")
    pb = f["premium_breakup"]
    for k, v in pb.items():
        L.append(f"| {v['field']} | {v['value']} | {v.get('page') or ''} | {v.get('confidence','')} |")
    L += ["", "## Ordered decision trace", ""]
    for s in out["trace"]:
        L.append(f"### {s['step']}. {s['title']}")
        L.append("")
        L.append(s["detail"])
        L.append("")
        for c in s["citations"]:
            L.append(f"- `{c['source']}` → `{c['locator']}`" + (f" = `{c['value']}`" if c['value'] is not None else "") + (f"  \n  _{c['note']}_" if c.get('note') else ""))
        L.append("")
    L += ["## All citations", ""]
    for c in out["citations"]:
        L.append(f"- **{c['kind']}** `{c['source']}` → `{c['locator']}`" + (f" = `{c['value']}`" if c['value'] is not None else "") + (f" — {c['note']}" if c.get('note') else ""))
    return "\n".join(L) + "\n"

for fp in sorted(FIX.glob("*.json")):
    name = fp.stem
    facts = facts_from_payload(json.loads(fp.read_text()), f"{name}.pdf", "fixture (hand-verified)")
    out = build_output(facts)
    (OUT / f"{name}.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    (OUT / f"{name}.md").write_text(md(name, out))
    print(f"{name}: {out['status']}  OD={out['rates']['od']['percent']}  TP={out['rates']['tp']['percent']}")
