/**
 * Typed client for the Autonomous Market & Competitor Analysis Agent backend.
 * Mirrors the Pydantic schemas in `backend/app/models/schemas.py`.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type SubjectType = "idea" | "product" | "company";
export type AnalysisDepth = "quick" | "standard" | "deep";
export type TaskStatus = "pending" | "in_progress" | "completed" | "failed";

export interface AnalyzeRequest {
  subject: string;
  subject_type: SubjectType;
  additional_context?: string | null;
  depth: AnalysisDepth;
}

export interface AnalyzeResponse {
  task_id: string;
  status: TaskStatus;
  message: string;
}

export interface SWOTAnalysis {
  strengths: string[];
  weaknesses: string[];
  opportunities: string[];
  threats: string[];
}

export interface Competitor {
  name: string;
  description: string;
  strengths: string[];
  weaknesses: string[];
  estimated_market_position?: string | null;
  website?: string | null;
}

export interface MarketTrend {
  title: string;
  description: string;
  impact: "high" | "medium" | "low";
}

export interface SourceCitation {
  title: string;
  url: string;
  snippet?: string | null;
}

export interface FinalReport {
  subject: string;
  executive_summary: string;
  swot: SWOTAnalysis;
  competitors: Competitor[];
  market_trends: MarketTrend[];
  sources: SourceCitation[];
  markdown_report: string;
}

export interface TaskStatusResponse {
  task_id: string;
  status: TaskStatus;
  progress?: string | null;
  created_at: string;
  updated_at: string;
  result?: FinalReport | null;
  error?: string | null;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      // response body wasn't JSON — fall back to statusText
    }
    throw new Error(`API request failed (${response.status}): ${detail}`);
  }
  return response.json() as Promise<T>;
}

export async function startAnalysis(
  payload: AnalyzeRequest
): Promise<AnalyzeResponse> {
  const response = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse<AnalyzeResponse>(response);
}

export async function fetchStatus(taskId: string): Promise<TaskStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/api/status/${taskId}`);
  return handleResponse<TaskStatusResponse>(response);
}

/**
 * Subscribes to live progress updates for a task via Server-Sent Events.
 * Returns the EventSource so the caller can close it on unmount.
 */
export function subscribeToStream(
  taskId: string,
  onUpdate: (status: TaskStatusResponse) => void,
  onError?: (event: Event) => void
): EventSource {
  const source = new EventSource(`${API_BASE_URL}/api/stream/${taskId}`);

  source.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as TaskStatusResponse;
      onUpdate(data);
      if (data.status === "completed" || data.status === "failed") {
        source.close();
      }
    } catch (err) {
      console.error("Failed to parse SSE payload", err);
    }
  };

  source.onerror = (event) => {
    onError?.(event);
  };

  return source;
}

/**
 * Polling fallback for environments where SSE isn't available (e.g. some
 * corporate proxies). Polls every `intervalMs` until the task reaches a
 * terminal state or `signal` is aborted.
 */
export async function pollStatus(
  taskId: string,
  onUpdate: (status: TaskStatusResponse) => void,
  { intervalMs = 2000, signal }: { intervalMs?: number; signal?: AbortSignal } = {}
): Promise<void> {
  while (!signal?.aborted) {
    const status = await fetchStatus(taskId);
    onUpdate(status);
    if (status.status === "completed" || status.status === "failed") {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}
