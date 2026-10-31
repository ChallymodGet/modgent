import React from 'react';
import { cn } from '../../utils/cn';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>((props, ref) => {
  const {
    className,
    variant = 'primary',
    size = 'md',
    isLoading = false,
    children,
    ...props_
  } = props;

  const variants = {
    primary: 'bg-accent text-accent-ink hover:bg-accent-hover',
    secondary: 'bg-surface-muted text-ink hover:bg-line',
    ghost: 'bg-transparent text-ink-soft hover:bg-surface-muted hover:text-ink',
    danger: 'bg-danger text-accent-ink hover:opacity-90',
  };

  const sizes = {
    sm: 'px-2.5 py-1 text-xs h-7',
    md: 'px-3.5 py-2 text-sm h-9',
    lg: 'px-5 py-2.5 text-sm h-11',
  };

  return (
    <button
      ref={ref}
      disabled={isLoading || props_.disabled}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-lg font-medium tracking-tight transition-transform duration-150 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-canvas disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]',
        variants[variant],
        sizes[size],
        className
      )}
      {...props_}
    >
      {isLoading ? (
        <span className="h-3.5 w-3.5 rounded-full border-2 border-current/30 border-t-current animate-spin" />
      ) : null}
      {children}
    </button>
  );
});

Button.displayName = 'Button';
