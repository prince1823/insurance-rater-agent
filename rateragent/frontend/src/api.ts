export const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ||
  "http://localhost:8000";

export type Rate = {
  applicable: boolean;
  percent: number | null;
  basis: string;
  note: string;
};

export type Citation = {
  source: string;
  locator: string;
  kind: "xlsx" | "pdf" | "policy";
  value: unknown;
  note: string;
};

export type TraceStep = {
  step: number;
  title: string;
  detail: string;
  citations: Citation[];
};

export type Analysis = {
  run_id?: string;
  created_at?: string;
  status: "resolved" | "unsupported" | "ambiguous";
  insurer: string;
  grid_file: string;
  policy_type: string;
  business_type: string;
  facts: Record<string, any>;
  rates: { od: Rate; tp: Rate };
  commission_amounts_inr: Record<string, number>;
  confidence: { level: string; reason: string };
  reason: string;
  clarifying_question: string | null;
  candidates: any[];
  citations: Citation[];
  trace: TraceStep[];
  extraction: { model: string; notes: string[]; source_file: string };
};

export type RunSummary = {
  id: string;
  created_at: string;
  filename: string;
  status: string;
  insurer: string;
  od_percent: string;
  tp_percent: string;
  model_used: string;
};

export async function listRuns(): Promise<RunSummary[]> {
  const r = await fetch(`${API_BASE}/runs`);
  if (!r.ok) throw new Error(`listRuns ${r.status}`);
  return (await r.json()).runs;
}

export async function getRun(id: string): Promise<Analysis> {
  const r = await fetch(`${API_BASE}/runs/${id}`);
  if (!r.ok) throw new Error(`getRun ${r.status}`);
  return (await r.json()).result;
}

export async function analyze(file: File): Promise<Analysis> {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch(`${API_BASE}/analyze`, { method: "POST", body: fd });
  const j = await r.json();
  if (!r.ok) throw new Error(j.detail || `analyze ${r.status}`);
  return j;
}

export async function analyzeFixture(name: string): Promise<Analysis> {
  const r = await fetch(`${API_BASE}/analyze?fixture=${encodeURIComponent(name)}`, {
    method: "POST",
  });
  const j = await r.json();
  if (!r.ok) throw new Error(j.detail || `analyze ${r.status}`);
  return j;
}

export const pdfUrl = (runId: string, page?: number) =>
  `${API_BASE}/runs/${runId}/pdf${page ? `#page=${page}` : ""}`;
