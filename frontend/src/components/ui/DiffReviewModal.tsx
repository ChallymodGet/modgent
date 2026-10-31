import React, { useEffect, useState } from 'react';
import { cn } from '../../utils/cn';
import { Button } from './Button';
import { X, FileText } from 'lucide-react';

interface DiffItem {
  id: string;
  question: string;
  draft: string;
  final: string;
  remembered?: boolean;
  choices?: string[];
  kind?: string;
}

interface DiffReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (finalAnswers: Record<string, string>) => void | Promise<void>;
  items: DiffItem[];
}

export const DiffReviewModal = ({ isOpen, onClose, onSubmit, items }: DiffReviewModalProps) => {
  const [editedAnswers, setEditedAnswers] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (isOpen) setEditedAnswers({});
  }, [isOpen, items]);

  if (!isOpen) return null;

  const handleUpdate = (id: string, value: string) => {
    setEditedAnswers((prev) => ({ ...prev, [id]: value }));
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      await onSubmit(editedAnswers);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-ink/40 p-4 backdrop-blur-[2px]">
      <div className="flex max-h-[82vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-line bg-surface shadow-card">
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <div>
            <h2 className="text-sm font-medium tracking-tight text-ink">Review drafted answers</h2>
            <p className="mt-0.5 text-xs text-ink-soft">The draft is what was filled on the form. Dropdowns list the site's options, and questions that say select all that apply can take more than one. The cover letter is at the top. Saving attaches it and continues. The agent never clicks Submit.</p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close review">
            <X size={16} strokeWidth={1.75} />
          </Button>
        </div>

        <div className="flex-1 space-y-6 overflow-y-auto px-5 py-5">
          {items.length === 0 ? (
            <p className="py-10 text-center text-sm text-ink-soft">No open-ended questions were found on this form.</p>
          ) : (
            items.map((item) => {
              const choices = item.choices || [];
              const multiple = item.kind === 'checkbox';
              const current = editedAnswers[item.id] ?? item.final ?? item.draft ?? '';
              const picked = new Set(
                (multiple ? current.split('\n') : [current]).map((part) => part.trim()).filter(Boolean)
              );
              const choose = (choice: string) => {
                if (!multiple) {
                  handleUpdate(item.id, choice);
                  return;
                }
                const next = new Set(picked);
                if (next.has(choice)) next.delete(choice);
                else next.add(choice);
                handleUpdate(item.id, [...next].join('\n'));
              };
              return (
              <div key={item.id} className="space-y-2">
                <div className="flex items-start gap-2">
                  <FileText size={14} strokeWidth={1.75} className="mt-0.5 shrink-0 text-ink-faint" />
                  <span className="text-sm font-medium text-ink">{item.question}</span>
                </div>
                <div className="rounded-xl bg-surface-muted p-3">
                  <span className="mb-2 block text-[11px] font-medium text-ink-faint">{item.remembered ? 'Remembered' : 'Draft'}</span>
                  <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink-soft">
                    {item.draft || 'Nothing selected yet'}
                  </p>
                </div>
                {choices.length > 0 ? (
                  <div className="rounded-xl border border-line bg-canvas p-3">
                    <span className="mb-2 block text-[11px] font-medium text-ink-faint">
                      {multiple ? 'Select all that apply' : 'Options from the form'}
                    </span>
                    {multiple || choices.length <= 8 ? (
                      <div className="flex flex-wrap gap-2">
                        {choices.map((choice) => (
                          <button
                            key={choice}
                            type="button"
                            onClick={() => choose(choice)}
                            className={cn(
                              'rounded-lg border px-2.5 py-1 text-left text-xs',
                              picked.has(choice) ? 'border-accent bg-accent/10 text-accent' : 'border-line text-ink-soft hover:text-ink'
                            )}
                          >
                            {choice}
                          </button>
                        ))}
                      </div>
                    ) : (
                      <select
                        className="w-full rounded-lg border border-line bg-canvas px-2 py-2 text-sm text-ink"
                        value={current}
                        onChange={(event) => handleUpdate(item.id, event.target.value)}
                      >
                        <option value="">Select...</option>
                        {choices.map((choice) => (
                          <option key={choice} value={choice}>{choice}</option>
                        ))}
                      </select>
                    )}
                  </div>
                ) : (
                  <div className="rounded-xl border border-line bg-canvas p-3">
                    <span className="mb-2 block text-[11px] font-medium text-ink-faint">Your version</span>
                    <textarea
                      className={cn(
                        'w-full resize-y bg-transparent text-sm leading-relaxed text-ink outline-none',
                        /cover letter/i.test(item.question) ? 'min-h-72' : 'h-28 resize-none'
                      )}
                      value={current}
                      onChange={(e) => handleUpdate(item.id, e.target.value)}
                    />
                  </div>
                )}
              </div>
              );
            })
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-line bg-surface-muted/60 px-5 py-3">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleSubmit} disabled={items.length === 0} isLoading={isSubmitting}>
            Save and continue
          </Button>
        </div>
      </div>
    </div>
  );
};
