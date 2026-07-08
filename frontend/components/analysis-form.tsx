'use client'

import { ArrowRight, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { SegmentedControl } from '@/components/segmented-control'
import { Button } from '@/components/ui/button'
import type { AnalysisDepth, AnalyzeRequest, SubjectType } from '@/lib/api'

interface AnalysisFormProps {
  onSubmit: (req: AnalyzeRequest) => void
  submitting?: boolean
  submitError?: string | null
  initial?: Partial<AnalyzeRequest>
}

const SUBJECT_OPTIONS: { value: SubjectType; label: string; hint: string }[] = [
  { value: 'idea', label: 'Idea', hint: 'Concept stage' },
  { value: 'product', label: 'Product', hint: 'In market' },
  { value: 'company', label: 'Company', hint: 'Established' },
]

const DEPTH_OPTIONS: { value: AnalysisDepth; label: string; hint: string }[] = [
  { value: 'quick', label: 'Quick', hint: '~1 min' },
  { value: 'standard', label: 'Standard', hint: 'Balanced' },
  { value: 'deep', label: 'Deep', hint: 'Exhaustive' },
]

export function AnalysisForm({
  onSubmit,
  submitting,
  submitError,
  initial,
}: AnalysisFormProps) {
  const [subject, setSubject] = useState(initial?.subject ?? '')
  const [subjectType, setSubjectType] = useState<SubjectType>(
    initial?.subject_type ?? 'idea',
  )
  const [depth, setDepth] = useState<AnalysisDepth>(initial?.depth ?? 'standard')
  const [context, setContext] = useState(initial?.additional_context ?? '')
  const [touched, setTouched] = useState(false)

  const valid = subject.trim().length > 0

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setTouched(true)
    if (!valid || submitting) return
    onSubmit({
      subject: subject.trim(),
      subject_type: subjectType,
      depth,
      additional_context: context.trim() ? context.trim() : null,
    })
  }

  return (
    <div className="mx-auto w-full max-w-3xl">
      {/* Hero */}
      <div className="mb-10 text-center">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium tracking-wide text-muted-foreground">
          <Sparkles className="size-3 text-primary" />
          Autonomous research agent
        </span>
        <h1 className="mt-6 text-balance font-serif text-4xl font-semibold leading-[1.05] tracking-tight sm:text-5xl md:text-6xl">
          VC-grade market analysis, on demand
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-pretty leading-relaxed text-muted-foreground">
          Describe any idea, product, or company. Meridian researches the market
          in real time and returns a structured report — SWOT, competitors, and
          trends with sources.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="rounded-2xl border border-border bg-card p-4 shadow-sm sm:p-6"
      >
        {/* Main input — hero search box */}
        <div className="relative">
          <label
            htmlFor="subject"
            className="mb-2 block text-xs font-medium uppercase tracking-wide text-muted-foreground"
          >
            Business idea, product, or company
          </label>
          <textarea
            id="subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            onKeyDown={(e) => {
              if (
                e.key === 'Enter' &&
                (e.metaKey || e.ctrlKey) &&
                !e.nativeEvent.isComposing
              ) {
                handleSubmit(e)
              }
            }}
            rows={3}
            placeholder="e.g. A collaborative workspace that combines docs, wikis, and project management for engineering teams…"
            aria-invalid={touched && !valid}
            className="w-full resize-none rounded-xl border border-border bg-background px-4 py-3.5 text-base leading-relaxed text-foreground shadow-inner outline-none transition-colors placeholder:text-muted-foreground/60 focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40 aria-[invalid=true]:border-destructive aria-[invalid=true]:ring-destructive/30"
          />
          {touched && !valid ? (
            <p className="mt-1.5 text-xs text-destructive">
              Please describe what you want analyzed.
            </p>
          ) : null}
        </div>

        {/* Selects */}
        <div className="mt-5 grid gap-5 sm:grid-cols-2">
          <div>
            <span className="mb-2 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Subject type
            </span>
            <SegmentedControl
              name="subject_type"
              label="Subject type"
              value={subjectType}
              options={SUBJECT_OPTIONS}
              onChange={setSubjectType}
            />
          </div>
          <div>
            <span className="mb-2 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Analysis depth
            </span>
            <SegmentedControl
              name="depth"
              label="Analysis depth"
              value={depth}
              options={DEPTH_OPTIONS}
              onChange={setDepth}
            />
          </div>
        </div>

        {/* Optional context */}
        <div className="mt-5">
          <label
            htmlFor="context"
            className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground"
          >
            Additional context
            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-normal normal-case tracking-normal text-muted-foreground">
              Optional
            </span>
          </label>
          <textarea
            id="context"
            value={context}
            onChange={(e) => setContext(e.target.value)}
            rows={2}
            placeholder="Target market, geography, constraints, positioning…"
            className="w-full resize-none rounded-xl border border-border bg-background px-4 py-3 text-sm leading-relaxed text-foreground outline-none transition-colors placeholder:text-muted-foreground/60 focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40"
          />
        </div>

        {submitError ? (
          <div className="mt-5 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {submitError}
          </div>
        ) : null}

        {/* Submit */}
        <div className="mt-6 flex flex-col items-center justify-between gap-3 sm:flex-row">
          <span className="hidden text-xs text-muted-foreground/80 sm:inline">
            Press ⌘ + Enter to run
          </span>
          <Button
            type="submit"
            disabled={submitting}
            className="h-11 w-full gap-2 rounded-xl px-6 text-sm font-semibold sm:w-auto"
          >
            {submitting ? (
              <>
                <span className="size-4 animate-spin rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground" />
                Starting…
              </>
            ) : (
              <>
                Analyze
                <ArrowRight className="size-4" />
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}
