import React, { useState, useEffect, useRef } from 'react';
import { cn } from '../utils/cn';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { JobCard, groupJobsByStatus, jobTableColumns } from '../components/ui/JobCard';
import { StatusBadge } from '../components/ui/StatusBadge';
import { AgentLogEntry } from '../components/ui/AgentLogEntry';
import { DiffReviewModal } from '../components/ui/DiffReviewModal';
import { DiscoveryScan, parseScanProgress } from '../components/ui/DiscoveryScan';
import { dayKey, formatDay, formatWhen, uniqueDays } from '../utils/dates';
import { LayoutDashboard, Briefcase, User, Terminal, Search, Loader2, FileUp, Save } from 'lucide-react';
import { useJobs, useAutomation, useProfile, useApplicationReview } from '../hooks/useAgent';
import { apiRequest } from '../utils/api';
import { useTheme } from '../hooks/useTheme';

export default function MainLayout() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [notice, setNotice] = useState<string | null>(null);
  const { theme, setTheme } = useTheme();
  const { jobs, isLoading: jobsLoading, refresh } = useJobs();
  const { tasks, activeTaskId, triggerDiscovery, triggerApply, triggerContinue } = useAutomation();
  const { isOpen: isReviewOpen, items: reviewItems, openReviewForJob, closeReview, submitReview } = useApplicationReview();

  const handleDiscovery = async () => {
    setNotice(null);
    try {
      await triggerDiscovery();
    } catch (err: any) {
      setNotice(err.message);
    }
  };

  const handleApply = async (jobId: string) => {
    setNotice(null);
    try {
      await triggerApply(jobId);
    } catch (err: any) {
      setNotice(err.message);
    }
  };

  const handleContinue = async (jobId: string) => {
    setNotice(null);
    try {
      await triggerContinue(jobId);
    } catch (err: any) {
      setNotice(err.message);
    }
  };

  const handleMarkApplied = async (jobId: string) => {
    setNotice(null);
    try {
      await apiRequest('PATCH', `/jobs/${jobId}`, { params: { status: 'Applied' } });
      await refresh();
    } catch (err: any) {
      setNotice(err.message);
    }
  };

  // Once an "apply" background task finishes pre-filling the form and
  // drafting AI answers, automatically surface the review modal so the
  // human can edit/confirm the answers before they're typed into the
  // still-open live application page.
  const handledApplyTasks = useRef<Set<string>>(new Set());
  const handledDiscoveryTasks = useRef<Set<string>>(new Set());
  useEffect(() => {
    Object.values(tasks).forEach((task: any) => {
      if (
        task.task_type === 'discovery' &&
        (task.status === 'completed' || task.status === 'failed') &&
        !handledDiscoveryTasks.current.has(task.task_id)
      ) {
        handledDiscoveryTasks.current.add(task.task_id);
        if (task.status === 'completed') refresh();
      }
      if (
        task.task_type === 'apply' &&
        (task.status === 'completed' || task.status === 'failed') &&
        !handledApplyTasks.current.has(task.task_id)
      ) {
        handledApplyTasks.current.add(task.task_id);
        let phase = '';
        try {
          phase = JSON.parse(task.progress || '{}').phase || '';
        } catch {
          phase = '';
        }
        if (task.status === 'completed' && phase === 'needs_you' && task.job_id) {
          openReviewForJob(task.job_id);
        } else if (task.result) {
          setNotice(task.result);
        }
        refresh();
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tasks]);

  const handleReviewSubmit = async (finalAnswers: Record<string, string>) => {
    try {
      const saved = await submitReview(finalAnswers);
      if (saved?.jobId) await triggerContinue(saved.jobId);
      refresh();
    } catch (err: any) {
      setNotice(err.message);
    }
  };

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-canvas text-ink">
      <aside className="flex w-[248px] shrink-0 flex-col border-r border-line bg-surface">
        <div className="px-4 pb-4 pt-5">
          <img
            src="/Logos/Primary%20logo.svg"
            alt="ModGent, your AI career agent"
            className="h-auto w-full dark:hidden"
          />
          <img
            src="/Logos/Dark-background%20logo.svg"
            alt="ModGent, your AI career agent"
            className="hidden h-auto w-full dark:block"
          />
        </div>

        <nav className="flex-1 space-y-0.5 px-3">
          <NavItem
            active={activeTab === 'dashboard'}
            onClick={() => setActiveTab('dashboard')}
            icon={<LayoutDashboard size={16} strokeWidth={1.75} />}
            label="Command Center"
          />
          <NavItem
            active={activeTab === 'jobs'}
            onClick={() => setActiveTab('jobs')}
            icon={<Briefcase size={16} strokeWidth={1.75} />}
            label="The Hunt"
          />
          <NavItem
            active={activeTab === 'profile'}
            onClick={() => setActiveTab('profile')}
            icon={<User size={16} strokeWidth={1.75} />}
            label="The Lab"
          />
          <NavItem
            active={activeTab === 'logs'}
            onClick={() => setActiveTab('logs')}
            icon={<Terminal size={16} strokeWidth={1.75} />}
            label="The Ledger"
          />
        </nav>

        <div className="border-t border-line px-4 py-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-ink-faint">Agent</span>
            <span className="inline-flex items-center gap-1.5 text-[11px] text-ink-soft">
              <span className={cn('h-1.5 w-1.5 rounded-full', activeTaskId ? 'bg-accent' : 'bg-success')} />
              {activeTaskId ? 'Working' : 'Idle'}
            </span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="relative flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex h-14 items-center justify-between border-b border-line bg-canvas px-6">
          <h2 className="text-sm font-medium tracking-tight text-ink">
            {activeTab === 'dashboard' && 'Command center'}
            {activeTab === 'jobs' && 'The hunt'}
            {activeTab === 'profile' && 'The lab'}
            {activeTab === 'logs' && 'The ledger'}
          </h2>

          <div className="flex items-center gap-3">
            <ThemeSwitch theme={theme} onChange={setTheme} />
            <Button
              variant="primary"
              size="sm"
              onClick={handleDiscovery}
              isLoading={!!activeTaskId}
            >
              <Search size={14} strokeWidth={1.75} />
              {activeTaskId ? 'Scanning' : 'Start discovery'}
            </Button>
          </div>
        </header>

        {activeTaskId && tasks[activeTaskId]?.task_type === 'discovery' && tasks[activeTaskId]?.status === 'running' && activeTab !== 'dashboard' && (
          <div className="flex items-center gap-3 border-b border-line bg-surface px-6 py-2">
            <span className="relative h-1.5 w-16 overflow-hidden rounded-full bg-surface-muted">
              <span className="absolute inset-y-0 w-1/2 bg-accent" style={{ animation: 'scan-sweep 1.8s linear infinite' }} />
            </span>
            <span className="text-xs text-ink-soft">
              {parseScanProgress(tasks[activeTaskId]?.progress)?.message || tasks[activeTaskId]?.result || 'Searching in the background'}
            </span>
          </div>
        )}

        {notice && (
          <div className="flex items-center justify-between gap-4 border-b border-line bg-surface px-6 py-2 text-sm text-ink">
            <span>{notice}</span>
            <button type="button" className="text-xs text-ink-faint hover:text-ink" onClick={() => setNotice(null)}>
              Dismiss
            </button>
          </div>
        )}

        <div className="flex-1 overflow-y-auto px-6 py-6">
          {activeTab === 'dashboard' && (
            <DashboardView
              jobs={jobs}
              logs={Object.values(tasks)}
              isLoading={jobsLoading}
              onApply={handleApply}
              onContinue={handleContinue}
              onMarkApplied={handleMarkApplied}
              scanning={tasks[activeTaskId || '']?.task_type === 'discovery' && tasks[activeTaskId || '']?.status === 'running'}
              scanProgress={parseScanProgress(tasks[activeTaskId || '']?.progress)}
              scanFallback={tasks[activeTaskId || '']?.result}
            />
          )}
          {activeTab === 'jobs' && (
            <JobsView jobs={jobs} isLoading={jobsLoading} onApply={handleApply} onContinue={handleContinue} onMarkApplied={handleMarkApplied} />
          )}
          {activeTab === 'profile' && <ProfileView />}
          {activeTab === 'logs' && <LogsView logs={Object.values(tasks)} />}
        </div>
      </main>

      <DiffReviewModal
        isOpen={isReviewOpen}
        onClose={closeReview}
        onSubmit={handleReviewSubmit}
        items={reviewItems}
      />
    </div>
  );
}

function NavItem({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm transition-colors',
        active
          ? 'bg-accent/10 font-semibold text-accent dark:text-accent-soft'
          : 'text-ink-soft hover:bg-surface-muted hover:text-ink'
      )}
    >
      {icon}
      {label}
    </button>
  );
}

function JobTable({ jobs, onApply, onContinue, onMarkApplied }: { jobs: any[]; onApply: (id: string) => void; onContinue: (id: string) => void; onMarkApplied: (id: string) => void }) {
  const groups = groupJobsByStatus(jobs);
  return (
    <div className="overflow-x-auto rounded-2xl border border-line bg-surface shadow-card">
      <div className="min-w-[40rem]">
      <div className={cn('grid items-center gap-4 border-b border-line px-4 py-2 text-[11px] text-ink-faint', jobTableColumns)}>
        <span>Role</span>
        <span>Match</span>
        <span className="text-right">Actions</span>
      </div>
      {groups.map((group) => (
        <div key={group.status}>
          <div className="flex items-center gap-2 border-b border-line bg-surface-muted/70 px-4 py-1.5">
            <StatusBadge status={group.status as React.ComponentProps<typeof StatusBadge>['status']} />
            <span className="font-mono text-[11px] tabular-nums text-ink-faint">{group.jobs.length}</span>
          </div>
          {group.jobs.map((job) => (
            <JobCard
              key={job.job_id}
              job={job}
              onApply={() => onApply(job.job_id)}
              onContinue={() => onContinue(job.job_id)}
              onMarkApplied={() => onMarkApplied(job.job_id)}
            />
          ))}
        </div>
      ))}
      </div>
    </div>
  );
}

function DashboardView({ jobs, logs, isLoading, onApply, onContinue, onMarkApplied, scanning, scanProgress, scanFallback }: { jobs: any[]; logs: any[]; isLoading: boolean; onApply: (id: string) => void; onContinue: (id: string) => void; onMarkApplied: (id: string) => void; scanning?: boolean; scanProgress?: ReturnType<typeof parseScanProgress>; scanFallback?: string }) {
  const jobDates = useDateSelection(jobs, (job) => job.date_added);
  const logDates = useDateSelection(logs, addedAt);
  if (isLoading) return <LoadingState />;

  const visibleJobs = jobs
    .filter((job) => jobDates.matches(job.date_added))
    .sort((a, b) => b.match_score - a.match_score)
    .slice(0, 6);
  const visibleLogs = logs
    .filter((log) => logDates.matches(addedAt(log)))
    .sort((a, b) => String(addedAt(b)).localeCompare(String(addedAt(a))));

  return (
    <div className="mx-auto grid max-w-6xl items-start gap-6 min-[1180px]:grid-cols-[minmax(0,1.7fr)_minmax(240px,0.85fr)]">
      <section className="min-w-0">
        <div className="mb-3 flex items-end justify-between gap-3">
          <div>
            <h3 className="text-sm font-medium tracking-tight text-ink">Priority queue</h3>
            <p className="mt-0.5 text-xs text-ink-soft">Highest matches, waiting on you.</p>
          </div>
          <DateFilter value={jobDates.selected} dates={jobDates.dates} onChange={jobDates.setSelected} />
        </div>
        {jobs.length === 0 ? (
          <EmptyState message="No jobs yet. Upload a CV in the lab, then start discovery." />
        ) : visibleJobs.length === 0 ? (
          <EmptyState message="Nothing was added on that date." />
        ) : (
          <JobTable jobs={visibleJobs} onApply={onApply} onContinue={onContinue} onMarkApplied={onMarkApplied} />
        )}
      </section>

      <section className="min-w-0">
        <div className="mb-3 flex items-end justify-between gap-3">
          <h3 className="text-sm font-medium tracking-tight text-ink">Activity</h3>
          <DateFilter value={logDates.selected} dates={logDates.dates} onChange={logDates.setSelected} />
        </div>
        {scanning ? (
          <DiscoveryScan progress={scanProgress ?? null} fallback={scanFallback} />
        ) : (
        <div className={cn('overflow-y-auto rounded-2xl border border-line bg-surface px-4 py-2 shadow-card', visibleLogs.length ? 'max-h-[70dvh]' : 'min-h-36')}>
          {logs.length === 0 ? (
            <p className="py-10 text-center text-xs text-ink-faint">Nothing running yet.</p>
          ) : visibleLogs.length === 0 ? (
            <p className="py-10 text-center text-xs text-ink-faint">Nothing was added on that date.</p>
          ) : (
            <div className="divide-y divide-line">
              {visibleLogs.map((log, i) => (
                <AgentLogEntry
                  key={log.task_id || i}
                  type={log.status === 'failed' ? 'error' : log.status === 'completed' ? 'success' : log.task_type === 'discovery' ? 'info' : 'ai'}
                  message={`${log.task_type} · ${log.status}${log.result ? `. ${log.result}` : ''}`}
                  timestamp={formatWhen(addedAt(log))}
                />
              ))}
            </div>
          )}
        </div>
        )}
      </section>
    </div>
  );
}

function JobsView({ jobs, isLoading, onApply, onContinue, onMarkApplied }: { jobs: any[]; isLoading: boolean; onApply: (id: string) => void; onContinue: (id: string) => void; onMarkApplied: (id: string) => void }) {
  const jobDates = useDateSelection(jobs, (job) => job.date_added);
  if (isLoading) return <LoadingState />;

  const visibleJobs = jobs
    .filter((job) => jobDates.matches(job.date_added))
    .sort((a, b) => String(b.date_added || '').localeCompare(String(a.date_added || '')) || b.match_score - a.match_score);

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <h3 className="text-sm font-medium tracking-tight text-ink">Every discovered role</h3>
          <p className="mt-0.5 text-xs text-ink-soft">
            {visibleJobs.length} on file{jobDates.selected !== 'all' ? ` · added ${formatDay(jobDates.selected)}` : ''}
          </p>
        </div>
        <DateFilter value={jobDates.selected} dates={jobDates.dates} onChange={jobDates.setSelected} />
      </div>
      {jobs.length === 0 ? (
        <EmptyState message="No jobs found." />
      ) : visibleJobs.length === 0 ? (
        <EmptyState message="Nothing was added on that date." />
      ) : (
        <JobTable jobs={visibleJobs} onApply={onApply} onContinue={onContinue} onMarkApplied={onMarkApplied} />
      )}
    </div>
  );
}

function ProfileView() {
  const { profile, isLoading, updateProfile, uploadCv } = useProfile();
  const [form, setForm] = useState<any>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');

  useEffect(() => {
    if (profile) setForm(profile);
  }, [profile]);

  if (isLoading || !form) {
    return <LoadingState />;
  }

  const setField = (key: string, value: any) => setForm((prev: any) => ({ ...prev, [key]: value }));
  const setRecurring = (key: string, value: string) =>
    setForm((prev: any) => ({ ...prev, recurring_answers: { ...prev.recurring_answers, [key]: value } }));

  const handleSave = async () => {
    setIsSaving(true);
    setSaveMessage('');
    try {
      await updateProfile({
        name: form.name,
        email: form.email,
        phone: form.phone,
        linkedin_url: form.linkedin_url,
        portfolio_url: form.portfolio_url,
        location: form.location,
        country: form.country,
        job_search_location: form.job_search_location,
        target_roles: form.target_roles,
        min_match_score: Number(form.min_match_score) || 0,
        recurring_answers: form.recurring_answers,
      });
      setSaveMessage('Saved.');
    } catch (err: any) {
      setSaveMessage(err.message || 'Failed to save.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    try {
      await uploadCv(file);
    } catch (err: any) {
      setSaveMessage(err.message || 'CV upload failed.');
    } finally {
      setIsUploading(false);
      e.target.value = '';
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-5 pb-12">
      <div>
        <h3 className="text-sm font-medium tracking-tight text-ink">Profile</h3>
        <p className="mt-0.5 max-w-[62ch] text-xs leading-relaxed text-ink-soft">
          Your name, contact details, and the answers that repeat on every application.
        </p>
      </div>

      <section className="space-y-3 rounded-2xl border border-line bg-surface p-5 shadow-card">
        <h4 className="flex items-center gap-2 text-sm font-medium text-ink">
          <FileUp size={15} strokeWidth={1.75} /> CV
        </h4>
        {form.has_cv ? (
          <p className="text-sm text-ink-soft">
            <span className="font-medium text-ink">{form.cv_filename}</span>
            {form.cv_uploaded_at && <span> · {new Date(form.cv_uploaded_at).toLocaleString()}</span>}
          </p>
        ) : (
          <p className="text-sm text-warning">Upload a PDF before you run discovery or apply.</p>
        )}
        <label className="inline-block">
          <input
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={handleCvUpload}
            disabled={isUploading}
          />
          <span
            className={cn(
              'inline-flex h-9 cursor-pointer items-center gap-2 rounded-lg bg-accent px-3.5 text-sm font-medium text-accent-ink transition-colors hover:bg-accent-hover',
              isUploading && 'pointer-events-none opacity-50'
            )}
          >
            {isUploading ? <Loader2 size={14} className="animate-spin" /> : <FileUp size={14} strokeWidth={1.75} />}
            {form.has_cv ? 'Replace PDF' : 'Upload PDF'}
          </span>
        </label>
      </section>

      <section className="space-y-4 rounded-2xl border border-line bg-surface p-5 shadow-card">
        <h4 className="text-sm font-medium text-ink">Contact</h4>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Input label="Full Name" value={form.name} onChange={(e) => setField('name', e.target.value)} />
          <Input label="Email" value={form.email} onChange={(e) => setField('email', e.target.value)} />
          <Input label="Phone" value={form.phone} onChange={(e) => setField('phone', e.target.value)} />
          <Input label="LinkedIn URL" value={form.linkedin_url} onChange={(e) => setField('linkedin_url', e.target.value)} />
          <Input label="Portfolio URL" value={form.portfolio_url} onChange={(e) => setField('portfolio_url', e.target.value)} />
          <Input label="Location (City, State)" value={form.location} onChange={(e) => setField('location', e.target.value)} />
          <Input label="Country" value={form.country} onChange={(e) => setField('country', e.target.value)} />
        </div>
      </section>

      {/* Job Search Preferences */}
      <section className="space-y-4 rounded-2xl border border-line bg-surface p-5 shadow-card">
        <h4 className="text-sm font-medium text-ink">Search</h4>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Input
            label="Target Roles (comma separated)"
            value={form.target_roles}
            onChange={(e) => setField('target_roles', e.target.value)}
          />
          <Input
            label="Job Search Location"
            value={form.job_search_location}
            onChange={(e) => setField('job_search_location', e.target.value)}
          />
          <Input
            label="Minimum Match Score (%)"
            type="number"
            min={0}
            max={100}
            value={form.min_match_score}
            onChange={(e) => setField('min_match_score', e.target.value)}
          />
        </div>
      </section>

      {/* Recurring Answers */}
      <section className="space-y-4 rounded-2xl border border-line bg-surface p-5 shadow-card">
        <h4 className="text-sm font-medium text-ink">Answers that repeat</h4>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Input
            label="Work Authorization"
            value={form.recurring_answers.work_authorization}
            onChange={(e) => setRecurring('work_authorization', e.target.value)}
          />
          <Input
            label="Require Sponsorship?"
            value={form.recurring_answers.sponsorship_required}
            onChange={(e) => setRecurring('sponsorship_required', e.target.value)}
          />
          <Input
            label="How did you hear about us?"
            value={form.recurring_answers.how_heard}
            onChange={(e) => setRecurring('how_heard', e.target.value)}
          />
          <Input
            label="Bound by Non-Compete?"
            value={form.recurring_answers.non_compete}
            onChange={(e) => setRecurring('non_compete', e.target.value)}
          />
          <Input
            label="Willing to Relocate?"
            value={form.recurring_answers.willing_to_relocate}
            onChange={(e) => setRecurring('willing_to_relocate', e.target.value)}
          />
          <Input
            label="Years of Experience"
            value={form.recurring_answers.years_experience}
            onChange={(e) => setRecurring('years_experience', e.target.value)}
          />
          <Input
            label="Salary Expectation"
            value={form.recurring_answers.salary_expectation}
            onChange={(e) => setRecurring('salary_expectation', e.target.value)}
          />
        </div>
      </section>

      <RememberedAnswers />

      <div className="flex items-center gap-3">
        <Button variant="primary" onClick={handleSave} isLoading={isSaving} className="gap-2">
          <Save size={14} />
          Save Profile
        </Button>
        {saveMessage && <span className="text-sm text-ink-soft">{saveMessage}</span>}
      </div>
    </div>
  );
}

function RememberedAnswers() {
  const [items, setItems] = useState<any[]>([]);

  const load = async () => {
    try {
      setItems(await apiRequest('GET', '/learned-answers'));
    } catch {
      setItems([]);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const forget = async (id: number) => {
    await apiRequest('DELETE', `/learned-answers/${id}`);
    setItems((current) => current.filter((item) => item.id !== id));
  };

  return (
    <section className="space-y-3 rounded-2xl border border-line bg-surface p-5 shadow-card">
      <div>
        <h4 className="text-sm font-medium text-ink">Remembered answers</h4>
        <p className="mt-0.5 text-xs leading-relaxed text-ink-soft">
          When you fill a blank the agent left empty, that answer is saved here and typed in the next time the same question appears.
        </p>
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-ink-faint">Nothing saved yet.</p>
      ) : (
        <ul className="divide-y divide-line">
          {items.map((item) => (
            <li key={item.id} className="flex items-start justify-between gap-3 py-3">
              <div className="min-w-0">
                <p className="text-sm text-ink">{item.question}</p>
                <p className="mt-1 line-clamp-3 text-xs leading-relaxed text-ink-soft">{item.answer}</p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => forget(item.id)}>
                Forget
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function LogsView({ logs }: { logs: any[] }) {
  const logDates = useDateSelection(logs, addedAt);
  const visibleLogs = logs
    .filter((log) => logDates.matches(addedAt(log)))
    .sort((a, b) => String(addedAt(b)).localeCompare(String(addedAt(a))));

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <h3 className="text-sm font-medium tracking-tight text-ink">Ledger</h3>
          <p className="mt-0.5 text-xs text-ink-soft">What the agent has done in this session.</p>
        </div>
        <DateFilter value={logDates.selected} dates={logDates.dates} onChange={logDates.setSelected} />
      </div>
      <div className="overflow-hidden rounded-2xl border border-line bg-surface px-4 py-2 shadow-card">
        {logs.length === 0 ? (
          <p className="py-10 text-center text-xs text-ink-faint">No entries yet.</p>
        ) : visibleLogs.length === 0 ? (
          <p className="py-10 text-center text-xs text-ink-faint">Nothing was added on that date.</p>
        ) : (
          <div className="divide-y divide-line font-mono">
            {visibleLogs.map((log, i) => (
              <AgentLogEntry
                key={log.task_id || i}
                type={log.status === 'failed' ? 'error' : log.status === 'completed' ? 'success' : 'info'}
                message={`${log.task_type} · ${log.status}${log.result ? ` · ${log.result}` : ''}`}
                timestamp={formatWhen(addedAt(log))}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function addedAt(entry: { created_at?: string; updated_at?: string }) {
  return entry.created_at || entry.updated_at;
}

function useDateSelection<T>(items: T[], getDate: (item: T) => string | undefined) {
  const [selected, setSelected] = useState('all');
  const dates = uniqueDays(items.map(getDate));
  const active = dates.includes(selected) ? selected : 'all';
  return {
    selected: active,
    dates,
    setSelected,
    matches: (value?: string) => active === 'all' || dayKey(value) === active,
  };
}

function DateFilter({ value, dates, onChange }: { value: string; dates: string[]; onChange: (value: string) => void }) {
  if (dates.length === 0) return null;
  return (
    <label className="flex shrink-0 items-center gap-2 text-[11px] font-medium tracking-wide text-ink-soft">
      Added
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-7 rounded-lg border border-line bg-surface px-2 text-xs font-normal text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
      >
        <option value="all">All dates</option>
        {dates.map((date) => (
          <option key={date} value={date}>
            {formatDay(date)}
          </option>
        ))}
      </select>
    </label>
  );
}

function ThemeSwitch({ theme, onChange }: { theme: 'light' | 'dark'; onChange: (theme: 'light' | 'dark') => void }) {
  return (
    <div className="grid grid-cols-2 rounded-lg bg-surface-muted p-0.5 text-xs" role="group" aria-label="Color theme">
      {(['light', 'dark'] as const).map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          aria-pressed={theme === option}
          className={cn(
            'h-7 rounded-md px-2.5 capitalize transition-colors',
            theme === option ? 'bg-surface font-medium text-ink shadow-card' : 'text-ink-soft hover:text-ink'
          )}
        >
          {option}
        </button>
      ))}
    </div>
  );
}

function LoadingState() {
  return (
    <div className="mx-auto max-w-6xl space-y-3">
      {[0, 1, 2].map((row) => (
        <div key={row} className="h-16 animate-pulse rounded-2xl bg-surface-muted" />
      ))}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-line px-6 py-16 text-center text-sm text-ink-soft">
      {message}
    </div>
  );
}

