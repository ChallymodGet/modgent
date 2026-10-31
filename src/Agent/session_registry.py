"""
Keeps a job's live Playwright browser session open between two separate API
calls:

1. POST /automation/apply/{job_id}          -> pre-fills the form, drafts
   open-ended answers with AI, and leaves the browser open.
2. POST /automation/apply/{job_id}/answers  -> types the human-reviewed,
   finalized answers into that SAME live page.

Without this registry, the browser context would close the instant the
background task function returned, making it impossible to act on the
form again afterwards — which is exactly the bug that caused "submitting
reviewed answers" to just flip a database flag instead of doing anything
real. Nothing here ever clicks Submit; that stays a manual, human action.
"""

import asyncio
from typing import Dict, Optional

_registry: Dict[str, dict] = {}
_lock = asyncio.Lock()


async def register_session(job_id: str, playwright, context, page) -> None:
    async with _lock:
        # If a stale session already exists for this job, close it first.
        existing = _registry.get(job_id)
        _registry[job_id] = {"playwright": playwright, "context": context, "page": page}
    if existing:
        await _teardown(existing)


async def get_session(job_id: str) -> Optional[dict]:
    async with _lock:
        return _registry.get(job_id)


async def close_session(job_id: str) -> bool:
    async with _lock:
        entry = _registry.pop(job_id, None)
    if entry is None:
        return False
    await _teardown(entry)
    return True


async def _teardown(entry: dict) -> None:
    try:
        await entry["context"].close()
    except Exception:
        pass
    try:
        await entry["playwright"].stop()
    except Exception:
        pass
