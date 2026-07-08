import { ArrowUpRight, Minus, Plus } from 'lucide-react'
import type { Competitor } from '@/lib/api'

interface CompetitorCardProps {
  competitor: Competitor
  index: number
}

export function CompetitorCard({ competitor, index }: CompetitorCardProps) {
  const { name, description, strengths, weaknesses, estimated_market_position } =
    competitor

  return (
    <div className="flex flex-col rounded-xl border border-border bg-card p-5 transition-colors hover:border-primary/40">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex size-8 items-center justify-center rounded-lg bg-muted font-mono text-xs font-semibold text-muted-foreground">
            {String(index + 1).padStart(2, '0')}
          </span>
          <div>
            <h3 className="font-serif text-lg font-semibold leading-tight tracking-tight">
              {name}
            </h3>
            {estimated_market_position ? (
              <span className="mt-0.5 inline-block rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                {estimated_market_position}
              </span>
            ) : null}
          </div>
        </div>
        {competitor.website ? (
          <a
            href={competitor.website}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            Site
            <ArrowUpRight className="size-3.5" />
          </a>
        ) : null}
      </div>

      <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
        {description}
      </p>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <TagBlock
          label="Strengths"
          items={strengths}
          icon={<Plus className="size-3 text-success" />}
          tone="success"
        />
        <TagBlock
          label="Weaknesses"
          items={weaknesses}
          icon={<Minus className="size-3 text-danger" />}
          tone="danger"
        />
      </div>
    </div>
  )
}

function TagBlock({
  label,
  items,
  icon,
  tone,
}: {
  label: string
  items: string[]
  icon: React.ReactNode
  tone: 'success' | 'danger'
}) {
  return (
    <div>
      <div className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {icon}
        {label}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {items.length === 0 ? (
          <span className="text-xs text-muted-foreground/60">—</span>
        ) : (
          items.map((item, i) => (
            <span
              key={i}
              className={`rounded-md px-2 py-1 text-xs leading-snug ring-1 ring-inset ${
                tone === 'success'
                  ? 'bg-success/10 text-foreground/90 ring-success/25'
                  : 'bg-danger/10 text-foreground/90 ring-danger/25'
              }`}
            >
              {item}
            </span>
          ))
        )}
      </div>
    </div>
  )
}
