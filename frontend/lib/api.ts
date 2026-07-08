// ---------------------------------------------------------------------------
// API types + client for the Autonomous Market & Competitor Analysis Agent.
// ---------------------------------------------------------------------------

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

export type SubjectType = 'idea' | 'product' | 'company'
export type AnalysisDepth = 'quick' | 'standard' | 'deep'
export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'failed'
export type ImpactLevel = 'high' | 'medium' | 'low'

export interface AnalyzeRequest {
  subject: string
  subject_type: SubjectType
  additional_context?: string | null
  depth: AnalysisDepth
}

export interface AnalyzeResponse {
  task_id: string
  status: 'pending'
  message: string
}

export interface SWOTAnalysis {
  strengths: string[]
  weaknesses: string[]
  opportunities: string[]
  threats: string[]
}

export interface Competitor {
  name: string
  description: string
  strengths: string[]
  weaknesses: string[]
  estimated_market_position?: string | null
  website?: string | null
}

export interface MarketTrend {
  title: string
  description: string
  impact: ImpactLevel
}

export interface SourceCitation {
  title: string
  url: string
  snippet?: string | null
}

export interface FinalReport {
  subject: string
  executive_summary: string
  swot: SWOTAnalysis
  competitors: Competitor[]
  market_trends: MarketTrend[]
  sources: SourceCitation[]
  markdown_report: string
}

export interface TaskStatusResponse {
  task_id: string
  status: TaskStatus
  progress?: string | null
  created_at: string
  updated_at: string
  result?: FinalReport | null
  error?: string | null
}

export class ApiError extends Error {
  status?: number
  constructor(message: string, status?: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/**
 * Kick off a new analysis. Returns the created task (HTTP 202).
 */
export async function startAnalysis(
  body: AnalyzeRequest,
  signal?: AbortSignal,
): Promise<AnalyzeResponse> {
  let res: Response
  try {
    res = await fetch(`${API_BASE_URL}/api/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    })
  } catch (err) {
    throw new ApiError(
      `Could not reach the analysis service at ${API_BASE_URL}. Is the backend running?`,
    )
  }

  if (!res.ok) {
    throw new ApiError(
      `Failed to start analysis (HTTP ${res.status}).`,
      res.status,
    )
  }

  return (await res.json()) as AnalyzeResponse
}

/**
 * One-shot status poll. Used as the fallback when SSE fails.
 */
export async function getStatus(
  taskId: string,
  signal?: AbortSignal,
): Promise<TaskStatusResponse> {
  let res: Response
  try {
    res = await fetch(`${API_BASE_URL}/api/status/${taskId}`, {
      method: 'GET',
      signal,
    })
  } catch (err) {
    throw new ApiError('Network error while polling task status.')
  }

  if (res.status === 404) {
    throw new ApiError('Analysis task was not found.', 404)
  }
  if (!res.ok) {
    throw new ApiError(`Failed to fetch status (HTTP ${res.status}).`, res.status)
  }

  return (await res.json()) as TaskStatusResponse
}

/**
 * The SSE stream URL for a given task.
 */
export function streamUrl(taskId: string): string {
  return `${API_BASE_URL}/api/stream/${taskId}`
}

export function subjectTypeLabel(t: SubjectType): string {
  return { idea: 'Idea', product: 'Product', company: 'Company' }[t]
}

export function depthLabel(d: AnalysisDepth): string {
  return { quick: 'Quick', standard: 'Standard', deep: 'Deep' }[d]
}
