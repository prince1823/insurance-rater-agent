import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Analysis,
  RunSummary,
  analyze,
  analyzeFixture,
  getRun,
  listRuns,
  pdfUrl,
} from "./api";

const SAMPLES = [
  "pvt-car-comprehensive-hdfc-ergo",
  "pvt-car-comprehensive-reliance",
  "pvt-car-satp-go-digit",
  "pvt-car-satp-tata-aig",
];

export default function App() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [page, setPage] = useState<number | undefined>();
  const [showPdf, setShowPdf] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      setRuns(await listRuns());
    } catch (e: any) {
      setErr(String(e.message || e));
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!selected) return;
    setPage(undefined);
    setShowPdf(false);
    getRun(selected).then(setAnalysis).catch((e) => setErr(String(e.message || e)));
  }, [selected]);

  async function runAnalysis(fn: () => Promise<Analysis>) {
    setBusy(true);
    setErr(null);
    try {
      const a = await fn();
      setAnalysis(a);
      setSelected(a.run_id ?? null);
      await refresh();
    } catch (e: any) {
      setErr(String(e.message || e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app">
      <header>
        <h1>Insurance Rater Agent</h1>
        <p className="sub">
          Upload a motor-policy PDF → extract facts → resolve the broker commission
          against the insurer grid → full source-cited decision trace.
        </p>
      </header>

      <div className="layout">
        <aside>
          <div
            className="drop"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              const f = e.dataTransfer.files?.[0];
              if (f) runAnalysis(() => analyze(f));
            }}
            onClick={() => fileRef.current?.click()}
          >
            <input
              ref={fileRef}
              type="file"
              accept="application/pdf"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) runAnalysis(() => analyze(f));
              }}
            />
            {busy ? "Analysing…" : "Drop a policy PDF here or click to upload"}
          </div>

          <details className="samples">
            <summary>Try a bundled sample</summary>
            {SAMPLES.map((s) => (
              <button key={s} disabled={busy} onClick={() => runAnalysis(() => analyzeFixture(s))}>
                {s}
              </button>
            ))}
          </details>

          {err && <div className="error">{err}</div>}

          <h3>Previous runs ({runs.length})</h3>
          <ul className="runs">
            {runs.map((r) => (
              <li
                key={r.id}
                className={r.id === selected ? "active" : ""}
                onClick={() => setSelected(r.id)}
              >
                <div className="runtop">
                  <span className={`badge ${r.status}`}>{r.status}</span>
                  <span className="ins">{r.insurer || "—"}</span>
                </div>
                <div className="runmeta">
                  {r.filename}
                  <br />
                  OD {r.od_percent} · TP {r.tp_percent} ·{" "}
                  {new Date(r.created_at).toLocaleString()}
                </div>
              </li>
            ))}
          </ul>
        </aside>

        <main>
          {!analysis && <div className="empty">Select a run or analyse a policy.</div>}
          {analysis && (
            <ResultView
              a={analysis}
              runId={selected}
              page={page}
              showPdf={showPdf}
              setShowPdf={setShowPdf}
              onCite={(p) => {
                if (p) {
                  setPage(p);
                  setShowPdf(true);
                }
              }}
            />
          )}
        </main>
      </div>
    </div>
  );
}

function ResultView({
  a,
  runId,
  page,
  showPdf,
  setShowPdf,
  onCite,
}: {
  a: Analysis;
  runId: string | null;
  page?: number;
  showPdf: boolean;
  setShowPdf: (fn: (v: boolean) => boolean) => void;
  onCite: (p?: number) => void;
}) {
  const factRows = useMemo(() => {
    const f = a.facts;
    const rows: [string, any, number | null, number | null][] = [];
    for (const [k, v] of Object.entries(f)) {
      if (k === "premium_breakup") continue;
      rows.push([v.field ?? k, v.value ?? v.normalised ?? "—", v.page ?? null, v.confidence ?? null]);
    }
    for (const v of Object.values<any>(f.premium_breakup)) {
      rows.push([v.field, v.value ?? "—", v.page ?? null, v.confidence ?? null]);
    }
    return rows;
  }, [a]);

  return (
    <div className="result">
      <div className="rhead">
        <span className={`badge big ${a.status}`}>{a.status}</span>
        <h2>{a.insurer}</h2>
        <span className="grid">grid: {a.grid_file || "—"}</span>
      </div>

      {a.reason && <div className="reason">{a.reason}</div>}
      {a.clarifying_question && (
        <div className="question">❓ {a.clarifying_question}</div>
      )}

      <div className="rates">
        <RateCard label="Own Damage (OD)" r={a.rates.od} amount={a.commission_amounts_inr.od} />
        <RateCard label="Third Party (TP)" r={a.rates.tp} amount={a.commission_amounts_inr.tp} />
      </div>

      <div className="conf">
        <b>Confidence: {a.confidence.level}</b> — {a.confidence.reason}
      </div>

      {a.candidates?.length > 0 && (
        <details className="candidates" open>
          <summary>Candidate interpretations ({a.candidates.length})</summary>
          <pre>{JSON.stringify(a.candidates, null, 2)}</pre>
        </details>
      )}

      <div className="cols">
        <section>
          <h3>Extracted facts</h3>
          <table className="facts">
            <thead>
              <tr>
                <th>Fact</th>
                <th>Value</th>
                <th>Pg</th>
                <th>Conf</th>
              </tr>
            </thead>
            <tbody>
              {factRows.map(([k, v, p, c], i) => (
                <tr key={i} className={c !== null && c < 0.55 ? "weak" : ""}>
                  <td>{k}</td>
                  <td>{String(v)}</td>
                  <td>
                    {p ? (
                      <a onClick={() => onCite(p)} className="pglink">
                        {p}
                      </a>
                    ) : (
                      ""
                    )}
                  </td>
                  <td>{c === null ? "" : c.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>Decision trace</h3>
          <ol className="trace">
            {a.trace.map((s) => (
              <li key={s.step}>
                <b>{s.title}</b>
                <p>{s.detail}</p>
                <ul>
                  {s.citations.map((c, i) => (
                    <li key={i} className="cite">
                      <code>{c.source}</code> →{" "}
                      {c.kind === "policy" && /page (\d+)/.test(c.locator) ? (
                        <a
                          className="pglink"
                          onClick={() =>
                            onCite(Number(/page (\d+)/.exec(c.locator)![1]))
                          }
                        >
                          {c.locator}
                        </a>
                      ) : (
                        <code>{c.locator}</code>
                      )}
                      {c.value != null && <> = <code>{String(c.value)}</code></>}
                      {c.note && <div className="cnote">{c.note}</div>}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>

          <details className="raw">
            <summary>Raw JSON output</summary>
            <pre>{JSON.stringify(a, null, 2)}</pre>
          </details>
        </section>

        <section className="pdfpane">
          <h3>
            Source PDF {page ? `(page ${page})` : ""}{" "}
            {runId && (
              <button className="pdftoggle" onClick={() => setShowPdf((v) => !v)}>
                {showPdf ? "hide" : "show"}
              </button>
            )}
          </h3>
          {!runId && <div className="empty">No stored PDF for this run.</div>}
          {runId && showPdf && (
            <iframe key={page} title="policy pdf" src={pdfUrl(runId, page)} />
          )}
          {runId && !showPdf && (
            <div className="empty">
              PDF hidden. Click “show”, or a page link in the trace, to open it.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function RateCard({
  label,
  r,
  amount,
}: {
  label: string;
  r: Analysis["rates"]["od"];
  amount?: number;
}) {
  return (
    <div className={`ratecard ${r.applicable ? "" : "na"}`}>
      <div className="rl">{label}</div>
      <div className="rv">
        {r.applicable ? (r.percent != null ? `${r.percent}%` : "—") : "not applicable"}
      </div>
      {r.applicable && r.basis && <div className="rb">on {r.basis}</div>}
      {amount != null && <div className="rb">≈ ₹{amount.toLocaleString()}</div>}
      {r.note && <div className="rn">{r.note}</div>}
    </div>
  );
}
