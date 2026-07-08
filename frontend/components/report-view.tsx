'use client'

import {
  Code2,
  ExternalLink,
  FileText,
  LayoutGrid,
  Plus,
  Quote,
} from 'lucide-react'
import { useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { CompetitorCard } from '@/components/competitor-card'
import { SwotGrid } from '@/components/swot-grid'
import { Button } from '@/components/ui/button'
import type { FinalReport, ImpactLevel } from '@/lib/api'
import { cn } from '@/lib/utils'

interface ReportViewProps {
  report: FinalReport
  onReset: () => void
}

type ViewMode = 'structured' | 'markdown'

export function ReportView({ report, onReset }: ReportViewProps) {
  const [view, setView] = useState<ViewMode>('structured')
  const [showJson, setShowJson] = useState(false)

  return (
    <div className="mx-auto w-full max-w-5xl animate-in fade-in slide-in-from-bottom-2 duration-500">
      {/* Report header */}
      <div className="flex flex-col gap-4 border-b border-border pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Market Analysis Report
          </span>
          <h1 className="mt-2 text-balance font-serif text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
            {report.subject}
          </h1>
        </div>
        <Button
          variant="outline"
          onClick={onReset}
          className="h-10 shrink-0 gap-2 rounded-xl px-4"
        >
          <Plus className="size-4" />
          New analysis
        </Button>
      </div>

      {/* View toggle */}
      <div className="mt-6 flex items-center justify-between gap-3">
        <div className="inline-flex rounded-xl border border-border bg-muted/50 p-1">
          <ToggleButton
            active={view === 'structured'}
            onClick={() => setView('structured')}
            icon={<LayoutGrid className="size-4" />}
            label="Structured"
          />
          <ToggleButton
            active={view === 'markdown'}
            onClick={() => setView('markdown')}
            icon={<FileText className="size-4" />}
            label="Report"
          />
        </div>
      </div>

      {/* Body */}
      {view === 'structured' ? (
        <div className="mt-6 space-y-10">
          {/* Executive summary */}
          <section>
            <div className="rounded-2xl border border-primary/25 bg-primary/[0.06] p-6 sm:p-7">
              <div className="flex items-center gap-2">
                <Quote className="size-4 text-primary" />
                <h2 className="text-xs font-semibold uppercase tracking-wide text-primary">
                  Executive Summary
                </h2>
              </div>
              <p className="mt-3 text-pretty text-lg leading-relaxed text-foreground/90">
                {report.executive_summary}
              </p>
            </div>
          </section>

          {/* SWOT */}
          <Section title="SWOT Analysis" count={undefined}>
            <SwotGrid swot={report.swot} />
          </Section>

          {/* Competitors */}
          <Section
            title="Competitive Landscape"
            count={report.competitors.length}
          >
            {report.competitors.length === 0 ? (
              <EmptyNote>No competitors identified.</EmptyNote>
            ) : (
              <div className="grid gap-4 lg:grid-cols-2">
                {report.competitors.map((c, i) => (
                  <CompetitorCard key={`${c.name}-${i}`} competitor={c} index={i} />
                ))}
              </div>
            )}
          </Section>

          {/* Market trends */}
          <Section title="Market Trends" count={report.market_trends.length}>
            {report.market_trends.length === 0 ? (
              <EmptyNote>No market trends identified.</EmptyNote>
            ) : (
              <ul className="space-y-3">
                {report.market_trends.map((t, i) => (
                  <li
                    key={`${t.title}-${i}`}
                    className="flex flex-col gap-2 rounded-xl border border-border bg-card p-5 sm:flex-row sm:items-start sm:justify-between"
                  >
                    <div className="pr-4">
                      <h3 className="font-semibold tracking-tight">{t.title}</h3>
                      <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                        {t.description}
                      </p>
                    </div>
                    <ImpactBadge impact={t.impact} />
                  </li>
                ))}
              </ul>
            )}
          </Section>

          {/* Sources */}
          <Section title="Sources" count={report.sources.length}>
            {report.sources.length === 0 ? (
              <EmptyNote>No sources cited.</EmptyNote>
            ) : (
              <ol className="space-y-2">
                {report.sources.map((s, i) => (
                  <li key={`${s.url}-${i}`}>
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="group flex gap-3 rounded-xl border border-transparent px-3 py-2.5 transition-colors hover:border-border hover:bg-muted/50"
                    >
                      <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-md bg-muted font-mono text-[11px] text-muted-foreground">
                        {i + 1}
                      </span>
                      <span className="min-w-0">
                        <span className="flex items-center gap-1.5 text-sm font-medium text-foreground">
                          <span className="truncate group-hover:text-primary">
                            {s.title}
                          </span>
                          <ExternalLink className="size-3.5 shrink-0 text-muted-foreground" />
                        </span>
                        {s.snippet ? (
                          <span className="mt-0.5 block text-xs leading-relaxed text-muted-foreground">
                            {s.snippet}
                          </span>
                        ) : null}
                        <span className="mt-0.5 block truncate font-mono text-[11px] text-muted-foreground/60">
                          {s.url}
                        </span>
                      </span>
                    </a>
                  </li>
                ))}
              </ol>
            )}
          </Section>
        </div>
      ) : (
        <div className="mt-6 rounded-2xl border border-border bg-card p-6 sm:p-10">
          <article className="prose prose-neutral max-w-none dark:prose-invert prose-headings:font-serif prose-headings:tracking-tight prose-a:text-primary prose-th:text-left prose-hr:border-border">
            <Markdown remarkPlugins={[remarkGfm]}>
              {report.markdown_report}
            </Markdown>
          </article>
        </div>
      )}

      {/* Debug footer */}
      <footer className="mt-12 border-t border-border pt-5">
        <button
          type="button"
          onClick={() => setShowJson((v) => !v)}
          className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <Code2 className="size-3.5" />
          {showJson ? 'Hide raw JSON' : 'View raw JSON'}
        </button>
        {showJson ? (
          <pre className="mt-3 max-h-96 overflow-auto rounded-xl border border-border bg-muted/40 p-4 font-mono text-xs leading-relaxed text-muted-foreground">
            {JSON.stringify(report, null, 2)}
          </pre>
        ) : null}
      </footer>
    </div>
  )
}

function Section({
  title,
  count,
  children,
}: {
  title: string
  count?: number
  children: React.ReactNode
}) {
  return (
    <section>
      <div className="mb-4 flex items-center gap-3">
        <h2 className="font-serif text-xl font-semibold tracking-tight">
          {title}
        </h2>
        {typeof count === 'number' ? (
          <span className="flex size-6 items-center justify-center rounded-full bg-muted font-mono text-xs text-muted-foreground">
            {count}
          </span>
        ) : null}
        <span className="h-px flex-1 bg-border" />
      </div>
      {children}
    </section>
  )
}

function ToggleButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean
  onClick: () => void
  icon: React.ReactNode
  label: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-sm font-medium transition-all',
        active
          ? 'bg-card text-foreground shadow-sm ring-1 ring-border'
          : 'text-muted-foreground hover:text-foreground',
      )}
    >
      {icon}
      {label}
    </button>
  )
}

function ImpactBadge({ impact }: { impact: ImpactLevel }) {
  const map: Record<ImpactLevel, { label: string; cls: string }> = {
    high: {
      label: 'High impact',
      cls: 'bg-danger/10 text-danger ring-danger/25',
    },
    medium: {
      label: 'Medium impact',
      cls: 'bg-warning/10 text-warning ring-warning/25',
    },
    low: {
      label: 'Low impact',
      cls: 'bg-success/10 text-success ring-success/25',
    },
  }
  const { label, cls } = map[impact]
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center gap-1.5 self-start rounded-full px-3 py-1 text-xs font-medium ring-1 ring-inset',
        cls,
      )}
    >
      <span className="size-1.5 rounded-full bg-current" />
      {label}
    </span>
  )
}

function EmptyNote({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-border bg-muted/30 px-5 py-8 text-center text-sm text-muted-foreground">
      {children}
    </div>
  )
}
