import React from 'react';

const BOARDS = ['LinkedIn', 'Indeed', 'Wellfound'] as const;

export interface ScanProgress {
  phase?: string;
  found?: number;
  message?: string;
  boards?: Record<string, string>;
  counts?: Record<string, number>;
}

export function parseScanProgress(raw: unknown): ScanProgress | null {
  if (!raw || typeof raw !== 'string') return null;
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : null;
  } catch {
    return null;
  }
}

export function DiscoveryScan({ progress, fallback }: { progress: ScanProgress | null; fallback?: string }) {
  const phase = progress?.phase;
  const boards = progress?.boards ?? {};
  const counts = progress?.counts ?? {};
  const message = progress?.message || fallback || 'Searching in the background';
  const found = progress?.found ?? 0;

  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-card">
      <div className="relative h-1 overflow-hidden bg-surface-muted">
        <div
          className="absolute inset-y-0 w-1/3 bg-accent/80"
          style={{ animation: 'scan-sweep 2.2s cubic-bezier(0.4, 0, 0.2, 1) infinite' }}
        />
      </div>

      <div className="space-y-4 px-4 py-4">
        <div className="flex items-end justify-between gap-3">
          <div>
            <p className="text-[11px] font-medium tracking-wide text-ink-faint">Background search</p>
            <p className="mt-1 text-sm font-medium tracking-tight text-ink">{message}</p>
          </div>
          <p className="font-mono text-2xl tabular-nums leading-none text-ink">{found}</p>
        </div>

        <div className="flex h-8 items-end gap-1" aria-hidden="true">
          {Array.from({ length: 18 }, (_, index) => (
            <span
              key={index}
              className="w-1 flex-1 origin-bottom rounded-full bg-accent/70"
              style={{
                height: `${30 + ((index * 17) % 70)}%`,
                animation: 'signal-bar 1.4s ease-in-out infinite',
                animationDelay: `${index * 70}ms`,
              }}
            />
          ))}
        </div>

        <ul className="space-y-2">
          {BOARDS.map((board) => {
            const state = boards[board] || 'waiting';
            const count = counts[board];
            const active = state === 'reading' || state === 'opening' || state === 'check';
            const label = phase === 'preparing'
              ? 'Waiting'
              : phase === 'scoring'
                ? 'Done'
                : state === 'check'
                  ? 'Needs you'
                  : state === 'opening'
                    ? 'Opening'
                    : state === 'reading'
                      ? (count ? String(count) : 'Reading')
                      : state === 'done'
                        ? (count != null ? String(count) : 'Done')
                        : 'Queued';
            return (
              <li key={board} className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-2 text-ink">
                  <span
                    className={
                      state === 'done' || phase === 'scoring'
                        ? 'h-1.5 w-1.5 rounded-full bg-success'
                        : state === 'check'
                          ? 'h-1.5 w-1.5 rounded-full bg-warning'
                          : active
                            ? 'h-1.5 w-1.5 rounded-full bg-accent'
                            : 'h-1.5 w-1.5 rounded-full bg-line'
                    }
                  />
                  {board}
                </span>
                <span className="font-mono tabular-nums text-ink-faint">{label}</span>
              </li>
            );
          })}
        </ul>
        <p className="text-[11px] leading-relaxed text-ink-faint">
          LinkedIn stays in the background. Indeed opens a window only when the site asks for a human check.
        </p>
      </div>
    </div>
  );
}
