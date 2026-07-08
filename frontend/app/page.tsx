'use client'

import { useCallback, useState } from 'react'
import { AnalysisForm } from '@/components/analysis-form'
import { ProgressView } from '@/components/progress-view'
import { ReportView } from '@/components/report-view'
import { SiteHeader } from '@/components/site-header'
import {
  type AnalyzeRequest,
  type FinalReport,
  ApiError,
  startAnalysis,
} from '@/lib/api'
import { SAMPLE_REPORT } from '@/lib/sample'

type Phase = 'form' | 'progress' | 'report'

export default function Page() {
  const [phase, setPhase] = useState<Phase>('form')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [request, setRequest] = useState<AnalyzeRequest | null>(null)
  const [report, setReport] = useState<FinalReport | null>(null)

  const handleSubmit = useCallback(async (req: AnalyzeRequest) => {
    setSubmitting(true)
    setSubmitError(null)
    setRequest(req)
    try {
      const res = await startAnalysis(req)
      setTaskId(res.task_id)
      setPhase('progress')
    } catch (err) {
      setSubmitError(
        err instanceof ApiError
          ? err.message
          : 'Something went wrong while starting the analysis.',
      )
    } finally {
      setSubmitting(false)
    }
  }, [])

  const handleComplete = useCallback((r: FinalReport) => {
    setReport(r)
    setPhase('report')
  }, [])

  const reset = useCallback(() => {
    setPhase('form')
    setTaskId(null)
    setReport(null)
    setSubmitError(null)
  }, [])

  const loadSample = useCallback(() => {
    setReport(SAMPLE_REPORT)
    setPhase('report')
  }, [])

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <SiteHeader />

      <main className="flex flex-1 flex-col px-5 py-12 sm:px-8 sm:py-16">
        {phase === 'form' ? (
          <div className="flex flex-1 flex-col items-center justify-center">
            <AnalysisForm
              onSubmit={handleSubmit}
              submitting={submitting}
              submitError={submitError}
              initial={request ?? undefined}
            />
            <button
              type="button"
              onClick={loadSample}
              className="mt-8 text-sm text-muted-foreground underline-offset-4 transition-colors hover:text-foreground hover:underline"
            >
              Or view a sample report →
            </button>
          </div>
        ) : null}

        {phase === 'progress' && taskId ? (
          <div className="flex flex-1 items-center justify-center">
            <ProgressView
              taskId={taskId}
              subject={request?.subject ?? 'your subject'}
              onComplete={handleComplete}
              onRetry={reset}
            />
          </div>
        ) : null}

        {phase === 'report' && report ? (
          <ReportView report={report} onReset={reset} />
        ) : null}
      </main>

      <footer className="border-t border-border/60 px-5 py-6 sm:px-8">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-2 text-center sm:flex-row sm:text-left">
          <p className="text-xs tracking-wide text-muted-foreground">
            Meridian · Autonomous Market Intelligence
          </p>
          <p className="text-xs text-muted-foreground">
            Reports are AI-generated. Verify before making decisions.
          </p>
        </div>
      </footer>
    </div>
  )
}
