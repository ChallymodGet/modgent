import React from 'react';
import { cn } from '../../utils/cn';
import { CheckCircle2, Loader2 } from 'lucide-react';

type StepStatus = 'completed' | 'active' | 'pending';

interface Step {
  id: string;
  label: string;
  status: StepStatus;
}

interface ApplicationStepperProps {
  steps: Step[];
  className?: string;
}

export const ApplicationStepper = ({ steps, className }: ApplicationStepperProps) => {
  return (
    <div className={cn('flex w-full items-center gap-2 py-4', className)}>
      {steps.map((step, index) => (
        <React.Fragment key={step.id}>
          <div className="flex flex-1 items-center gap-3">
            <div
              className={cn(
                'flex h-8 w-8 items-center justify-center rounded-full border transition-colors',
                step.status === 'completed' && 'border-success bg-success/10',
                step.status === 'active' && 'border-accent bg-accent/10',
                step.status === 'pending' && 'border-line bg-surface'
              )}
            >
              {step.status === 'completed' && <CheckCircle2 size={16} className="text-success" />}
              {step.status === 'active' && <Loader2 size={16} className="animate-spin text-accent" />}
              {step.status === 'pending' && <div className="h-1.5 w-1.5 rounded-full bg-ink-faint" />}
            </div>
            <span className={cn('text-xs font-medium', step.status === 'active' ? 'text-ink' : 'text-ink-soft')}>
              {step.label}
            </span>
          </div>
          {index < steps.length - 1 && (
            <div className={cn('h-px flex-1', steps[index].status === 'completed' ? 'bg-success' : 'bg-line')} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
};
