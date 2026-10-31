import React from 'react';
import { cn } from '../../utils/cn';

interface ConfidenceIndicatorProps {
  score: number;
  className?: string;
}

export const ConfidenceIndicator = ({ score, className }: ConfidenceIndicatorProps) => {
  const clamped = Math.max(0, Math.min(100, score));
  const tone = clamped >= 80 ? 'bg-success' : clamped >= 50 ? 'bg-warning' : 'bg-danger';

  return (
    <div className={cn('flex w-28 items-center gap-2', className)}>
      <div className="h-1 flex-1 overflow-hidden rounded-full bg-surface-muted">
        <div className={cn('h-full rounded-full', tone)} style={{ width: `${clamped}%` }} />
      </div>
      <span className="w-8 text-right font-mono text-[11px] tabular-nums text-ink-soft">{clamped}</span>
    </div>
  );
};
