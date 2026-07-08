'use client'

import { cn } from '@/lib/utils'

export interface SegmentOption<T extends string> {
  value: T
  label: string
  hint?: string
}

interface SegmentedControlProps<T extends string> {
  value: T
  options: SegmentOption<T>[]
  onChange: (value: T) => void
  name: string
  label: string
}

export function SegmentedControl<T extends string>({
  value,
  options,
  onChange,
  name,
  label,
}: SegmentedControlProps<T>) {
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className="grid auto-cols-fr grid-flow-col gap-1 rounded-xl border border-border bg-muted/50 p-1"
    >
      {options.map((opt) => {
        const active = opt.value === value
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            name={name}
            onClick={() => onChange(opt.value)}
            className={cn(
              'flex flex-col items-center gap-0.5 rounded-lg px-3 py-2 text-sm font-medium transition-all outline-none focus-visible:ring-2 focus-visible:ring-ring',
              active
                ? 'bg-card text-foreground shadow-sm ring-1 ring-border'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <span>{opt.label}</span>
            {opt.hint ? (
              <span className="text-[10px] font-normal tracking-tight text-muted-foreground/80">
                {opt.hint}
              </span>
            ) : null}
          </button>
        )
      })}
    </div>
  )
}
