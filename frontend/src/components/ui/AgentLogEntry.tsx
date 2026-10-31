import React from 'react';
import { cn } from '../../utils/cn';
import { CheckCircle2, AlertCircle, Loader2, Search } from 'lucide-react';

interface LogEntryProps {
  type: 'info' | 'success' | 'error' | 'ai';
  message: string;
  timestamp?: string;
  className?: string;
}

export const AgentLogEntry = ({ type, message, timestamp, className }: LogEntryProps) => {
  const typeStyles = {
    info: { icon: <Search size={13} strokeWidth={1.75} className="text-ink-faint" /> },
    success: { icon: <CheckCircle2 size={13} strokeWidth={1.75} className="text-success" /> },
    error: { icon: <AlertCircle size={13} strokeWidth={1.75} className="text-danger" /> },
    ai: { icon: <Loader2 size={13} strokeWidth={1.75} className="text-accent" /> },
  };

  const style = typeStyles[type];

  return (
    <div className={cn('flex items-start gap-2.5 py-2', className)}>
      <div className="mt-0.5 shrink-0">{style.icon}</div>
      <div className="min-w-0 flex-1">
        <p className="text-xs leading-relaxed text-ink-soft">{message}</p>
        {timestamp && (
          <span className="mt-0.5 block font-mono text-[10px] tabular-nums text-ink-faint">{timestamp}</span>
        )}
      </div>
    </div>
  );
};
