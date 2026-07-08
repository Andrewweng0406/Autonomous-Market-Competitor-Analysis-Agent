import { Shield, TrendingUp, TriangleAlert, Zap } from 'lucide-react'
import type { SWOTAnalysis } from '@/lib/api'
import { cn } from '@/lib/utils'

interface SwotGridProps {
  swot: SWOTAnalysis
}

const QUADRANTS = [
  {
    key: 'strengths' as const,
    title: 'Strengths',
    icon: Shield,
    accent: 'text-success',
    dot: 'bg-success',
    border: 'border-success/25',
    tint: 'bg-success/[0.06]',
  },
  {
    key: 'weaknesses' as const,
    title: 'Weaknesses',
    icon: TriangleAlert,
    accent: 'text-danger',
    dot: 'bg-danger',
    border: 'border-danger/25',
    tint: 'bg-danger/[0.06]',
  },
  {
    key: 'opportunities' as const,
    title: 'Opportunities',
    icon: TrendingUp,
    accent: 'text-info',
    dot: 'bg-info',
    border: 'border-info/25',
    tint: 'bg-info/[0.06]',
  },
  {
    key: 'threats' as const,
    title: 'Threats',
    icon: Zap,
    accent: 'text-warning',
    dot: 'bg-warning',
    border: 'border-warning/25',
    tint: 'bg-warning/[0.06]',
  },
]

export function SwotGrid({ swot }: SwotGridProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {QUADRANTS.map((q) => {
        const items = swot[q.key] ?? []
        const Icon = q.icon
        return (
          <div
            key={q.key}
            className={cn(
              'rounded-xl border p-5',
              q.border,
              q.tint,
            )}
          >
            <div className="flex items-center gap-2">
              <Icon className={cn('size-4', q.accent)} />
              <h3 className="text-sm font-semibold tracking-tight">
                {q.title}
              </h3>
              <span className="ml-auto font-mono text-xs text-muted-foreground">
                {items.length}
              </span>
            </div>
            <ul className="mt-3 space-y-2">
              {items.length === 0 ? (
                <li className="text-sm text-muted-foreground/70">
                  No items identified.
                </li>
              ) : (
                items.map((item, i) => (
                  <li key={i} className="flex gap-2.5 text-sm leading-relaxed">
                    <span
                      className={cn(
                        'mt-1.5 size-1.5 shrink-0 rounded-full',
                        q.dot,
                      )}
                    />
                    <span className="text-foreground/90">{item}</span>
                  </li>
                ))
              )}
            </ul>
          </div>
        )
      })}
    </div>
  )
}
