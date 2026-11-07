import React, { useEffect, useRef, useState } from 'react';
import { cn } from '../../utils/cn';
import { Button } from './Button';
import { ConfidenceIndicator } from './ConfidenceIndicator';
import { MapPin, ExternalLink, MoreHorizontal } from 'lucide-react';
import { formatDay } from '../../utils/dates';

interface CardAction {
  label: string;
  onClick?: () => void;
  variant: 'primary' | 'secondary';
}

interface JobCardProps {
  job: {
    title: string;
    company: string;
    location: string;
    match_score: number;
    status: string;
    url: string;
    date_added?: string;
  };
  onApply?: () => void;
  onContinue?: () => void;
  onSetStatus?: (status: string) => void;
  className?: string;
}

const waitingOnYou = new Set(['Pending Review', 'Ready to Submit', 'Needs you']);
// What can happen after the user has applied. Set by hand; the agent never does.
const nextSteps: Record<string, string[]> = {
  Applied: ['Interviewing', 'Ghosted'],
  Interviewing: ['Offer', 'Ghosted'],
  Ghosted: ['Interviewing'],
};
const visibleActionCount = 2;
const statusOrder = ['Needs you', 'Pending Review', 'Ready to Submit', 'Not Reviewed', 'Interviewing', 'Offer', 'Applied', 'Ghosted'];

export const jobTableColumns = 'grid-cols-[minmax(12rem,1fr)_7.5rem_11.5rem]';

export function groupJobsByStatus<T extends { status: string }>(jobs: T[]) {
  const groups = new Map<string, T[]>();
  for (const job of jobs) {
    const rows = groups.get(job.status) ?? [];
    rows.push(job);
    groups.set(job.status, rows);
  }
  return [...groups.entries()]
    .sort(([a], [b]) => {
      const aIndex = statusOrder.indexOf(a);
      const bIndex = statusOrder.indexOf(b);
      return (aIndex === -1 ? statusOrder.length : aIndex) - (bIndex === -1 ? statusOrder.length : bIndex);
    })
    .map(([status, rows]) => ({ status, jobs: rows }));
}

export const JobCard = ({ job, onApply, onContinue, onSetStatus, className }: JobCardProps) => {
  const waiting = waitingOnYou.has(job.status);
  const steps = nextSteps[job.status];
  const actions: CardAction[] = waiting
    ? [
        { label: 'Continue', onClick: onContinue, variant: 'primary' },
        { label: 'Apply', onClick: onApply, variant: 'secondary' },
        { label: 'Mark applied', onClick: () => onSetStatus?.('Applied'), variant: 'secondary' },
      ]
    : steps
      ? steps.map((status) => ({ label: status, onClick: () => onSetStatus?.(status), variant: 'secondary' as const }))
      : job.status === 'Not Reviewed'
        ? [{ label: 'Apply', onClick: onApply, variant: 'primary' }]
        : [];
  const visible = actions.slice(0, visibleActionCount);
  const overflow = actions.slice(visibleActionCount);
  return (
    <article
      className={cn(
        'group grid items-center gap-4 border-b border-line bg-surface px-4 py-3.5 last:border-b-0',
        jobTableColumns,
        className
      )}
    >
      <div className="min-w-0">
        <h3 className="truncate text-sm font-medium tracking-tight text-ink">{job.title}</h3>
        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-ink-soft">
          <span className="truncate">{job.company}</span>
          <span className="text-ink-faint">·</span>
          <span className="inline-flex min-w-0 items-center gap-1">
            <MapPin size={12} strokeWidth={1.75} className="shrink-0" />
            <span className="truncate">{job.location}</span>
          </span>
          {job.date_added && (
            <span className="font-mono text-[11px] tabular-nums text-ink-faint">Added {formatDay(job.date_added)}</span>
          )}
        </div>
      </div>

      <ConfidenceIndicator score={job.match_score} />

      <div className="flex items-center justify-end gap-1">
        <a
          href={job.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex h-7 w-7 items-center justify-center rounded-lg text-ink-faint transition-colors hover:bg-surface-muted hover:text-ink"
          title="Open the original posting"
        >
          <ExternalLink size={14} strokeWidth={1.75} />
        </a>
        {overflow.length > 0 && <MoreActions actions={overflow} />}
        {[...visible].reverse().map((action) => (
          <Button key={action.label} variant={action.variant} size="sm" onClick={action.onClick}>
            {action.label}
          </Button>
        ))}
      </div>
    </article>
  );
};

function MoreActions({ actions }: { actions: CardAction[] }) {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ top: 0, left: 0 });

  useEffect(() => {
    if (!open) return;

    const place = () => {
      const rect = buttonRef.current?.getBoundingClientRect();
      if (!rect) return;
      const width = 168;
      const height = actions.length * 36 + 8;
      const top = rect.bottom + 6 + height > window.innerHeight ? rect.top - height - 6 : rect.bottom + 6;
      const left = Math.max(8, Math.min(rect.right - width, window.innerWidth - width - 8));
      setPosition({ top, left });
    };

    const closeOnOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (menuRef.current?.contains(target) || buttonRef.current?.contains(target)) return;
      setOpen(false);
    };

    const close = () => setOpen(false);
    place();
    document.addEventListener('mousedown', closeOnOutside);
    window.addEventListener('resize', place);
    window.addEventListener('scroll', close, true);
    return () => {
      document.removeEventListener('mousedown', closeOnOutside);
      window.removeEventListener('resize', place);
      window.removeEventListener('scroll', close, true);
    };
  }, [open, actions.length]);

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        aria-label="More actions"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
        className="inline-flex h-7 w-7 items-center justify-center rounded-lg text-ink-faint transition-colors hover:bg-surface-muted hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        <MoreHorizontal size={16} strokeWidth={1.75} />
      </button>
      {open && (
        <div
          ref={menuRef}
          role="menu"
          style={{ top: position.top, left: position.left }}
          className="fixed z-50 w-[168px] rounded-lg border border-line bg-surface p-1 shadow-card"
        >
          {actions.map((action) => (
            <button
              key={action.label}
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                action.onClick?.();
              }}
              className="flex w-full rounded-md px-2.5 py-1.5 text-left text-sm text-ink hover:bg-surface-muted"
            >
              {action.label}
            </button>
          ))}
        </div>
      )}
    </>
  );
}
