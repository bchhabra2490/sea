import type {
  BotDocsResponse,
  BotChatResponse,
  BotClassifyResponse,
  BotHistoryResponse,
  BotStatusResponse,
  InsightsResponse,
  JobStartResponse,
  PipelineStatusResponse,
  ResetDataResponse,
} from "@/types";

const API_BASE = "";

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    const detail = body.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((d: { msg?: string }) => d.msg ?? JSON.stringify(d)).join("; ");
    }
    return body.message ?? res.statusText;
  } catch {
    return res.statusText;
  }
}

export async function fetchInsights(): Promise<InsightsResponse> {
  const res = await fetch(`${API_BASE}/insights`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchPipelineStatus(): Promise<PipelineStatusResponse> {
  const res = await fetch(`${API_BASE}/pipeline/status`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function startAnalysis(
  force = true,
  inputPath?: string
): Promise<JobStartResponse> {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      force_recompute: force,
      ...(inputPath ? { input_path: inputPath } : {}),
    }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

/** Load data/sample_conversations.jsonl into Supabase, then run the pipeline. */
export async function startSampleAnalysis(force = true): Promise<JobStartResponse> {
  const res = await fetch(`${API_BASE}/analyze/sample`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ force_recompute: force }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchBotDocs(): Promise<BotDocsResponse> {
  const res = await fetch(`${API_BASE}/bot/docs`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchBotStatus(): Promise<BotStatusResponse> {
  const res = await fetch(`${API_BASE}/bot/status`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchBotHistory(limit = 50): Promise<BotHistoryResponse> {
  const res = await fetch(`${API_BASE}/bot/history?limit=${limit}`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function sendBotChat(message: string, topK = 3): Promise<BotChatResponse> {
  const res = await fetch(`${API_BASE}/bot/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, top_k: topK }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function classifyMessage(
  message: string,
  topK = 3
): Promise<BotClassifyResponse> {
  const res = await fetch(`${API_BASE}/bot/classify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, top_k: topK }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function resetAllData(): Promise<ResetDataResponse> {
  const res = await fetch(`${API_BASE}/data/reset`, { method: "POST" });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function startUploadAnalysis(
  file: File,
  force = true
): Promise<JobStartResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("force_recompute", String(force));

  const res = await fetch(`${API_BASE}/analyze/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}
