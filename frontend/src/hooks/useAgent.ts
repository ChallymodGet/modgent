import { useState, useEffect, useRef, useCallback } from 'react';
import { apiRequest, apiUpload } from '../utils/api';

export function useJobs() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchJobs = async (status?: string) => {
    setIsLoading(true);
    try {
      const url = status ? `/jobs?status=${status}` : '/jobs';
      const data = await apiRequest('GET', url);
      setJobs(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  return { jobs, isLoading, error, refresh: fetchJobs };
}

export function useAutomation() {
  const [tasks, setTasks] = useState<Record<string, any>>({});
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);

  const pollTask = (taskId: string) => {
    const interval = setInterval(async () => {
      try {
        const status = await apiRequest('GET', `/automation/tasks/${taskId}`);
        setTasks(prev => ({ ...prev, [taskId]: status }));
        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(interval);
          setActiveTaskId(current => (current === taskId ? null : current));
        }
      } catch (e) {
        clearInterval(interval);
      }
    }, 1500);
  };

  const triggerDiscovery = async () => {
    const data = await apiRequest('POST', '/automation/discovery');
    const taskId = data.task_id;
    setActiveTaskId(taskId);
    pollTask(taskId);
    return taskId;
  };

  // candidate_summary used to be a hardcoded placeholder the caller had to
  // pass in — it's now always derived server-side from the candidate's
  // actual uploaded CV, so applying only needs the job id.
  const triggerApply = async (jobId: string) => {
    const data = await apiRequest('POST', `/automation/apply/${jobId}`);
    const taskId = data.task_id;
    pollTask(taskId);
    return taskId;
  };

  const triggerContinue = async (jobId: string) => {
    const data = await apiRequest('POST', `/automation/apply/${jobId}/continue`);
    const taskId = data.task_id;
    pollTask(taskId);
    return taskId;
  };

  return { tasks, activeTaskId, triggerDiscovery, triggerApply, triggerContinue };
}

export function useProfile() {
  const [profile, setProfile] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProfile = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await apiRequest('GET', '/profile');
      setProfile(data);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const updateProfile = async (update: Record<string, any>) => {
    const data = await apiRequest('PUT', '/profile', { body: update });
    setProfile(data);
    return data;
  };

  const uploadCv = async (file: File) => {
    const data = await apiUpload('/profile/cv', file);
    setProfile(data);
    return data;
  };

  return { profile, isLoading, error, refresh: fetchProfile, updateProfile, uploadCv };
}

/**
 * Drives the "review AI-drafted answers before they're typed into the real
 * application form" flow: fetches the drafted answers for a job, shows them
 * in the review modal, then sends the human-finalized versions back to the
 * API — which types them into the still-open browser session.
 */
export function useApplicationReview() {
  const [reviewJobId, setReviewJobId] = useState<string | null>(null);
  const [items, setItems] = useState<any[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const itemsRef = useRef(items);
  itemsRef.current = items;

  const openReviewForJob = async (jobId: string) => {
    const answers = await apiRequest('GET', `/automation/apply/${jobId}/questions`);
    const mapped = answers.map((a: any) => {
      const choices = String(a.choices || '')
        .split('\n')
        .map((choice: string) => choice.trim())
        .filter(Boolean);
      const question = String(a.question || '');
      const kind = a.kind || (/select all that apply/i.test(question) ? 'checkbox' : choices.length ? 'select' : 'text');
      return {
        id: String(a.answer_id),
        question,
        draft: a.draft_answer,
        final: a.final_answer || a.draft_answer,
        remembered: Boolean(a.remembered),
        choices,
        kind,
      };
    });
    mapped.sort((a: { question: string }, b: { question: string }) => {
      const cover = (item: { question: string }) => /cover letter/i.test(item.question) ? 0 : 1;
      return cover(a) - cover(b);
    });
    setItems(mapped);
    setReviewJobId(jobId);
    setIsOpen(true);
  };

  const closeReview = () => {
    setIsOpen(false);
    setReviewJobId(null);
    setItems([]);
  };

  const submitReview = async (finalAnswers: Record<string, string>) => {
    if (!reviewJobId) return null;
    const jobId = reviewJobId;
    // DiffReviewModal only reports fields the user actually edited — for
    // anything left untouched, the AI draft itself is the final answer.
    const payload = itemsRef.current.map(item => ({
      answer_id: Number(item.id),
      final_answer: finalAnswers[item.id] !== undefined ? finalAnswers[item.id] : item.draft,
    }));
    const result = await apiRequest('POST', `/automation/apply/${jobId}/answers`, { body: payload });
    closeReview();
    return { jobId, result };
  };

  return { isOpen, items, openReviewForJob, closeReview, submitReview };
}
