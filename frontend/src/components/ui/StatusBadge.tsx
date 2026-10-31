import React from 'react';
import { cn } from '../../utils/cn';

interface StatusBadgeProps {
  status: 'Applied' | 'Pending Review' | 'Ready to Submit' | 'Needs you' | 'Interviewing' | 'Ghosted' | 'Offer' | 'Not Reviewed';
  className?: string;
}

export const StatusBadge = ({ status, className }: StatusBadgeProps) => {
  const statusStyles: Record<StatusBadgeProps['status'], string> = {
    Applied: 'bg-success/12 text-success',
    'Pending Review': 'bg-info/12 text-info',
    'Ready to Submit': 'bg-warning/14 text-warning',
    'Needs you': 'bg-warning/14 text-warning',
    Interviewing: 'bg-info/12 text-info',
    Ghosted: 'bg-surface-muted text-ink-faint',
    Offer: 'bg-success text-accent-ink',
    'Not Reviewed': 'bg-surface-muted text-ink-soft',
  };

  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center rounded-md px-1.5 py-0.5 text-[10px] font-medium tracking-wide',
        statusStyles[status] ?? 'bg-surface-muted text-ink-soft',
        className
      )}
    >
      {status}
    </span>
  );
};
