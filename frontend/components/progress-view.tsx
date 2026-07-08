'use client'

import { AlertTriangle, RotateCcw } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  type FinalReport,
  type TaskStatus,
  getStatus,
  streamUrl,
  type TaskStatusResponse,
} from '@/lib/api'
import { cn } from '@/lib/utils'

interface ProgressViewProps {
  taskId: string
  subject: string
  onComplete: (report: FinalReport) => void
  onRetry: () => void
}

const STATUS_LABEL: Record<TaskStatus, string> = {
  pending: 'Queued',
  in_progress: 'Researching',
  completed: 'Complete',
  failed: 'Failed',
}

const STAGES = [
  'Planning research strategy',
  'Gathering market signals',
  'Mapping competitors',
  'Synthesizing findings',
]

export function ProgressView({
  taskId,
  subject,
  onComplete,
  onRetry,
}: ProgressViewProps) {
  const [status, setStatus] = useState<TaskStatus>('pending')
  const [messages, setMessages] = useState<string[]>([
    'Connecting to research engine…',
  ])
  const [error, setError] = useState<string | null>(null)

  const doneRef = useRef(false)

  useEffect(() => {
    doneRef.current = false
    let cancelled = false
    let es: EventSource | null = null
    let pollTimer: ReturnType<typeof setTimeout> | null = null
    let polling = false

    function pushMessage(msg?: string | null) {
      if (!msg) return
      setMessages((prev) => {
        if (prev[prev.length - 1] === msg) return prev
        return [...prev, msg].slice(-6)
      })
    }

    function handleStatus(data: TaskStatusResponse) {
      if (cancelled) return
      setStatus(data.status)
      pushMessage(data.progress)

      if (data.status === 'completed' && data.result) {
        doneRef.current = true
        pushMessage('Analysis complete.')
        es?.close()
        if (pollTimer) clearTimeout(pollTimer)
        // brief beat so the user sees the "complete" state
        setTimeout(() => {
          if (!cancelled) onComplete(data.result as FinalReport)
        }, 650)
      } else if (data.status === 'failed') {
        doneRef.current = true
        es?.close()
        if (pollTimer) clearTimeout(pollTimer)
        setError(data.error ?? 'The analysis failed unexpectedly.')
      }
    }

    async function startPolling() {
      if (polling || doneRef.current) return
      polling = true
      const tick = async () => {
        if (cancelled || doneRef.current) return
        try {
          const s = await getStatus(taskId)
          handleStatus(s)
          if (!cancelled && !doneRef.current) {
            pollTimer = setTimeout(tick, 2000)
          }
        } catch (err) {
          if (!cancelled) {
            setError(
              err instanceof Error
                ? err.message
                : 'Lost connection to the analysis service.',
            )
          }
        }
      }
      tick()
    }

    try {
      es = new EventSource(streamUrl(taskId))
      es.onmessage = (ev) => {
        try {
          handleStatus(JSON.parse(ev.data) as TaskStatusResponse)
        } catch {
          /* ignore malformed frames */
        }
      }
      es.onerror = () => {
        es?.close()
        if (!doneRef.current) startPolling()
      }
    } catch {
      startPolling()
    }

    return () => {
      cancelled = true
      es?.close()
      if (pollTimer) clearTimeout(pollTimer)
    }
  }, [taskId, onComplete])

  if (error) {
    return (
      <div className="mx-auto w-full max-w-lg animate-in fade-in zoom-in-95 duration-300">
        <div className="rounded-2xl border border-destructive/30 bg-card p-8 text-center shadow-sm">
          <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
            <AlertTriangle className="size-6" />
          </div>
          <h2 className="mt-5 font-serif text-2xl font-semibold">
            Analysis failed
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            {error}
          </p>
          <Button
            onClick={onRetry}
            className="mt-6 h-10 gap-2 rounded-xl px-5"
          >
            <RotateCcw className="size-4" />
            Back to form
          </Button>
        </div>
      </div>
    )
  }

  const current = messages[messages.length - 1]
  const isDone = status === 'completed'

  return (
    <div className="mx-auto w-full max-w-2xl">
      <div className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-10">
        {/* Status indicator */}
        <div className="flex items-center gap-3">
          <span
            className={cn(
              'size-2 shrink-0 rounded-full bg-primary',
              !isDone && 'animate-pulse',
            )}
          />
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {STATUS_LABEL[status]}
          </span>
        </div>

        <h2 className="mt-6 text-balance font-serif text-2xl font-semibold leading-tight sm:text-3xl">
          Analyzing{' '}
          <span className="text-primary">{truncate(subject, 64)}</span>
        </h2>

        {/* Live narration */}
        <div className="mt-6 min-h-[3.5rem] rounded-xl border border-border bg-muted/40 px-4 py-3.5">
          <div className="flex items-start gap-2.5">
            <span className="mt-1 size-1.5 shrink-0 animate-pulse rounded-full bg-primary" />
            <p
              key={current}
              className="animate-in fade-in slide-in-from-bottom-1 text-sm font-medium leading-relaxed text-foreground duration-500"
            >
              {current}
            </p>
          </div>
        </div>

        {/* History log */}
        {messages.length > 1 ? (
          <ul className="mt-4 space-y-1.5">
            {messages.slice(0, -1).map((m, i) => (
              <li
                key={`${m}-${i}`}
                className="flex items-center gap-2 text-xs text-muted-foreground/70"
              >
                <span className="text-primary/70">✓</span>
                <span className="truncate">{m}</span>
              </li>
            ))}
          </ul>
        ) : null}

        {/* Stage rail */}
        <div className="mt-8 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {STAGES.map((stage, i) => {
            const activeIndex = Math.min(
              messages.length - 1,
              STAGES.length - 1,
            )
            const reached = isDone || i <= activeIndex
            return (
              <div key={stage} className="flex flex-col gap-1.5">
                <div
                  className={cn(
                    'h-1 rounded-full transition-colors duration-500',
                    reached ? 'bg-primary' : 'bg-border',
                  )}
                />
                <span
                  className={cn(
                    'text-[11px] leading-tight transition-colors',
                    reached ? 'text-foreground' : 'text-muted-foreground/50',
                  )}
                >
                  {stage}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function truncate(s: string, n: number) {
  return s.length > n ? `${s.slice(0, n).trimEnd()}…` : s
}
