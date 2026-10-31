import React from 'react';
import { cn } from '../../utils/cn';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>((props, ref) => {
  const { label, error, className, ...props_ } = props;

  return (
    <div className="flex w-full flex-col gap-1.5">
      {label && (
        <label className="text-[11px] font-medium tracking-wide text-ink-soft">
          {label}
        </label>
      )}
      <input
        ref={ref}
        className={cn(
          'h-9 rounded-lg border border-line bg-canvas px-3 text-sm text-ink outline-none transition-colors placeholder:text-ink-faint focus:border-accent focus:ring-2 focus:ring-accent/20 disabled:opacity-50',
          error && 'border-danger focus:border-danger focus:ring-danger/20',
          className
        )}
        {...props_}
      />
      {error && (
        <span className="text-[11px] font-medium text-danger">{error}</span>
      )}
    </div>
  );
});

Input.displayName = 'Input';
