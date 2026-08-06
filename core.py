#!/usr/bin/env python3
"""
ALGERNON — fleet orchestration engine.

The gift: let ANY assistant dispatch tightly-scoped parallel sub-tasks to a
fleet of cheap workers, collect the results, and stay free to think.
"Orchestrate a fleet, spend fewer tokens."

This module is the pure engine — NO MCP dependency, so it is directly testable.
It is provider-agnostic: sub-agents run on the CALLER'S OWN LLM key. Set either

    ANTHROPIC_API_KEY                       -> https://api.anthropic.com/v1/messages
    OPENAI_API_KEY (+ optional OPENAI_BASE_URL) -> OpenAI-compatible /chat/completions

The user brings the key; Algernon brings the orchestration.

Self-contained: pure stdlib + httpx. Zero imports from any private substrate.
Apache-2.0. (c) ZagAIrot Technologies LLC.
"""
from __future__ import annotations

import os
import json
import asyncio
from typing import Any

# httpx is imported lazily inside _llm so the pure engine stays importable and
# testable (monkeypatch _llm) even where the HTTP stack isn't installed yet.

# --- configuration (all env-overridable; nothing hard-coded to one vendor) ----
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

# The whole pitch is "a fleet of CHEAP workers", so the defaults are the small,
# fast tier of each provider. Override per call (model=...) or per process (env).
DEFAULT_ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5")
DEFAULT_OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

DEFAULT_MAX_TOKENS = int(os.environ.get("ALGERNON_MAX_TOKENS", "2048"))
HTTP_TIMEOUT = float(os.environ.get("ALGERNON_HTTP_TIMEOUT", "120"))


def _provider() -> str:
    """Pick the provider from whatever key the caller supplied."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return "none"


async def _llm(prompt: str, system: str | None = None, model: str | None = None) -> dict:
    """
    One provider-agnostic LLM call over async httpx.

    Returns a dict — {"text": "..."} on success, or {"error": "..."} on any
    failure. It NEVER raises, so callers (dispatch/plan) can rely on it always
    returning something structured.
    """
    provider = _provider()

    try:
        import httpx  # lazy: only needed for a real network call

        if provider == "anthropic":
            key = os.environ["ANTHROPIC_API_KEY"]
            body: dict[str, Any] = {
                "model": model or DEFAULT_ANTHROPIC_MODEL,
                "max_tokens": DEFAULT_MAX_TOKENS,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                body["system"] = system
            headers = {
                "x-api-key": key,
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
            }
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                r = await client.post(ANTHROPIC_URL, headers=headers, json=body)
            if r.status_code != 200:
                return {"error": f"anthropic {r.status_code}: {r.text[:500]}"}
            data = r.json()
            text = "".join(
                block.get("text", "")
                for block in data.get("content", [])
                if block.get("type") == "text"
            )
            u = data.get("usage") or {}
            return {"text": text, "usage": {
                "input_tokens": u.get("input_tokens"),
                "output_tokens": u.get("output_tokens"),
            }}

        if provider == "openai":
            key = os.environ["OPENAI_API_KEY"]
            base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            body = {
                "model": model or DEFAULT_OPENAI_MODEL,
                "messages": messages,
                "max_tokens": DEFAULT_MAX_TOKENS,
            }
            headers = {
                "Authorization": f"Bearer {key}",
                "content-type": "application/json",
            }
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                r = await client.post(f"{base}/chat/completions", headers=headers, json=body)
            if r.status_code != 200:
                return {"error": f"openai {r.status_code}: {r.text[:500]}"}
            data = r.json()
            text = data["choices"][0]["message"].get("content", "") or ""
            u = data.get("usage") or {}
            return {"text": text, "usage": {
                "input_tokens": u.get("prompt_tokens"),
                "output_tokens": u.get("completion_tokens"),
            }}

        return {
            "error": "no LLM key found — set ANTHROPIC_API_KEY or OPENAI_API_KEY "
                     "(the fleet runs on YOUR key)."
        }
    except Exception as exc:  # noqa: BLE001 — deliberately swallow everything
        return {"error": f"{type(exc).__name__}: {exc}"}


def _extract_json(text: str) -> Any:
    """
    Pull the first JSON array/object out of an LLM response, tolerating
    ```json fences and surrounding prose. Raises ValueError if none is found.
    """
    stripped = text.strip()
    # Strip a leading code fence if present.
    if stripped.startswith("```"):
        stripped = stripped.split("```", 2)[1]
        if stripped.lstrip().startswith("json"):
            stripped = stripped.lstrip()[4:]
    stripped = stripped.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    # Fall back: locate the outermost [...] or {...} span.
    for opener, closer in (("[", "]"), ("{", "}")):
        start = stripped.find(opener)
        end = stripped.rfind(closer)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(stripped[start:end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("no JSON found in model output")


async def dispatch(tasks: list[dict], model: str | None = None, max_parallel: int = 8) -> list[dict]:
    """
    Run N tightly-scoped tasks CONCURRENTLY on the fleet.

    tasks: [{"id": str, "prompt": str}, ...]
    Returns: [{"id": str, "result": str|None, "error": str|None}, ...]

    The core value: N tight tasks in parallel beats one bloated serial prompt —
    each worker sees only its own scope, so it spends fewer tokens, and the
    orchestrator stays free to think while the fleet works.
    """
    if not tasks:
        return []

    sem = asyncio.Semaphore(max(1, int(max_parallel)))

    async def _run(task: dict) -> dict:
        tid = task.get("id")
        prompt = task.get("prompt", "")
        if not prompt:
            return {"id": tid, "result": None, "error": "empty prompt"}
        async with sem:
            out = await _llm(prompt, model=model)
        if "error" in out:
            return {"id": tid, "result": None, "error": out["error"]}
        # usage (input/output token counts) is passed straight through when the
        # provider reports it — so callers can see exactly what the fleet spent.
        return {"id": tid, "result": out.get("text", ""), "error": None,
                "usage": out.get("usage")}

    return await asyncio.gather(*(_run(t) for t in tasks))


_PLAN_SYSTEM = (
    "You are a task-decomposition planner for a fleet of parallel LLM workers. "
    "Given a goal, split it into exactly {k} INDEPENDENT sub-tasks that can each "
    "run on its own, in parallel, with NO shared state and NO dependency on the "
    "output of another sub-task. Scope each sub-task as TIGHTLY as possible: give "
    "each worker only what it needs and nothing more — tight scoping is the "
    "token-efficiency lever, because a narrow prompt makes a worker spend fewer "
    "tokens and return a sharper result. "
    "Respond with ONLY a JSON array of objects, each {{\"id\": \"t1\", "
    "\"prompt\": \"...\"}}, no prose, no code fence."
)


async def plan(goal: str, k: int = 4, model: str | None = None) -> list[dict]:
    """
    Decompose a goal into k tightly-scoped, independent sub-task prompts using
    a single LLM call. Returns [{"id": str, "prompt": str}, ...].

    Raises RuntimeError if the planning call fails or returns unusable output —
    callers (e.g. orchestrate) are expected to catch it.
    """
    k = max(1, int(k))
    system = _PLAN_SYSTEM.format(k=k)
    out = await _llm(f"GOAL: {goal}", system=system, model=model)
    if "error" in out:
        raise RuntimeError(f"plan failed: {out['error']}")

    try:
        parsed = _extract_json(out.get("text", ""))
    except ValueError as exc:
        raise RuntimeError(f"plan produced no parseable task list: {exc}")

    if not isinstance(parsed, list):
        raise RuntimeError("plan did not return a JSON array of tasks")

    tasks: list[dict] = []
    for i, item in enumerate(parsed, start=1):
        if isinstance(item, dict) and item.get("prompt"):
            tasks.append({"id": item.get("id") or f"t{i}", "prompt": str(item["prompt"])})
        elif isinstance(item, str) and item.strip():
            tasks.append({"id": f"t{i}", "prompt": item.strip()})
    if not tasks:
        raise RuntimeError("plan returned an empty task list")
    return tasks


async def orchestrate(goal: str, k: int = 4, model: str | None = None, max_parallel: int = 8) -> dict:
    """
    plan THEN dispatch, in one call. Decompose the goal into k tight sub-tasks,
    fan them out across the fleet, and return both the plan and the results.

    Returns {"goal", "tasks", "results"} on success, or {"goal", "error"} if
    planning failed.
    """
    try:
        tasks = await plan(goal, k=k, model=model)
    except RuntimeError as exc:
        return {"goal": goal, "error": str(exc)}
    results = await dispatch(tasks, model=model, max_parallel=max_parallel)
    return {"goal": goal, "tasks": tasks, "results": results}
