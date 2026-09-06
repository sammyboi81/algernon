#!/usr/bin/env python3
"""
Algernon frugality benchmark — reproducible by a skeptic, no paid key required.

WHAT IT MEASURES (honestly)
---------------------------
It runs the SAME batch of N tight, independent sub-tasks two ways and measures
real token usage + wall-clock for each:

  SOLO   — the orchestrator does the whole job itself, in ONE growing context
           (one LLM call that must ingest all N sub-tasks and generate every
           answer). This is "the mind drowning in one serial job."

  FANOUT — Algernon's real dispatch() path: the N sub-tasks are fanned out to a
           fleet of cheap workers, each seeing ONLY its own slice. The
           orchestrator generates none of the answers itself.

Both modes hit the SAME model so the comparison is fair. The DEFAULT worker is
your LOCAL ollama (127.0.0.1:11434, llama3.2:3b) so ANYONE can reproduce this
for free — no API key, no account, no telemetry.

It prints the real numbers and does NOT hide the trade-offs: fan-out usually
spends MORE total tokens (each worker re-pays a little prompt overhead), and
wall-clock only improves if your worker fleet actually runs requests in
parallel. The honest, always-true win is the OFFLOAD: the expensive
orchestrator stops generating the grind itself and stops holding the whole job
in one context — a cheap fleet does that instead.

USAGE
-----
    python -m benchmark                 # default: local ollama, N=6
    ALG_BENCH_N=10 python -m benchmark  # more sub-tasks

To benchmark a paid provider instead, just set that provider's env vars
(ANTHROPIC_API_KEY, or OPENAI_API_KEY [+ OPENAI_BASE_URL / OPENAI_MODEL])
before running; the benchmark auto-detects and will not touch ollama.
"""
from __future__ import annotations

import os
import sys
import time
import json
import asyncio
import urllib.request

# --- default to free, local ollama so a skeptic can reproduce with zero cost ---
# Ollama exposes an OpenAI-compatible endpoint; Algernon's engine speaks it
# natively. We only set these if the caller has NOT chosen their own provider.
OLLAMA_URL = os.environ.get("ALG_BENCH_OLLAMA_URL", "http://127.0.0.1:11434")
if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "ollama"  # ollama ignores the value
    os.environ.setdefault("OPENAI_BASE_URL", f"{OLLAMA_URL}/v1")
    os.environ.setdefault("OPENAI_MODEL", "llama3.2:3b")

# import the REAL engine (same code the MCP server calls) AFTER env is set
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from algernon_mcp import core  # noqa: E402

N = int(os.environ.get("ALG_BENCH_N", "6"))

# Fixed, deterministic, genuinely-independent sub-tasks. Tight scope + a one-
# sentence cap keeps outputs bounded so a skeptic's numbers land close to these.
_BANK = [
    "Define a mutex in operating systems",
    "Define a semaphore in operating systems",
    "Define a spinlock in operating systems",
    "Define a deadlock in operating systems",
    "Define a race condition in operating systems",
    "Define a condition variable in operating systems",
    "Define a barrier synchronization primitive",
    "Define a read-write lock",
    "Define a monitor in concurrent programming",
    "Define starvation in operating systems",
]
TASKS = [
    {"id": f"t{i+1}", "prompt": f"{_BANK[i % len(_BANK)]}. Answer in ONE sentence."}
    for i in range(N)
]


def _tok(u: dict | None, key: str) -> int:
    if not u:
        return 0
    return int(u.get(key) or 0)


def _ollama_up() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


async def run_solo() -> dict:
    """One call: the orchestrator ingests all N sub-tasks and answers them all."""
    joined = "\n".join(f"{i+1}. {t['prompt']}" for i, t in enumerate(TASKS))
    prompt = (
        f"Answer ALL {N} of the following independent questions. "
        f"Number each answer to match, and keep each answer to ONE sentence.\n\n"
        f"{joined}"
    )
    t0 = time.perf_counter()
    out = await core._llm(prompt)
    dt = time.perf_counter() - t0
    if "error" in out:
        raise RuntimeError(f"SOLO call failed: {out['error']}")
    u = out.get("usage")
    return {
        "seconds": dt,
        "in": _tok(u, "input_tokens"),
        "out": _tok(u, "output_tokens"),
        "calls": 1,
    }


async def run_fanout() -> dict:
    """Algernon's real dispatch() path: N tight tasks across the cheap fleet."""
    t0 = time.perf_counter()
    results = await core.dispatch(TASKS, max_parallel=N)
    dt = time.perf_counter() - t0
    errs = [r for r in results if r.get("error")]
    if errs:
        raise RuntimeError(f"FANOUT had {len(errs)} failed task(s): {errs[0]['error']}")
    ins = [_tok(r.get("usage"), "input_tokens") for r in results]
    outs = [_tok(r.get("usage"), "output_tokens") for r in results]
    return {
        "seconds": dt,
        "in": sum(ins),
        "out": sum(outs),
        "calls": len(results),
        "max_worker_in": max(ins) if ins else 0,
        "avg_worker_in": (sum(ins) / len(ins)) if ins else 0,
    }


def _pct(a: float, b: float) -> str:
    if b == 0:
        return "n/a"
    return f"{(a - b) / b * 100:+.0f}%"


def main() -> int:
    provider = core._provider()
    model = (
        os.environ.get("OPENAI_MODEL")
        if provider == "openai"
        else os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5")
    )
    print("=" * 72)
    print("ALGERNON FRUGALITY BENCHMARK")
    print("=" * 72)
    print(f"provider : {provider}   model: {model}")
    print(f"sub-tasks: {N} tight, independent tasks (one-sentence answers)")
    print()

    if provider == "none":
        print("No LLM provider available. Set a provider key, or start ollama.")
        return 2
    if provider == "openai" and OLLAMA_URL in os.environ.get("OPENAI_BASE_URL", ""):
        if not _ollama_up():
            print(f"ollama not reachable at {OLLAMA_URL}.")
            print("Install from https://ollama.com, then:  ollama pull llama3.2:3b")
            return 2

    solo = asyncio.run(run_solo())
    fan = asyncio.run(run_fanout())

    solo_total = solo["in"] + solo["out"]
    fan_total = fan["in"] + fan["out"]

    # ---- results table -----------------------------------------------------
    print(f"{'metric':<40}{'SOLO (do-it-itself)':>16}{'ALGERNON fan-out':>18}")
    print("-" * 74)
    print(f"{'LLM calls':<40}{solo['calls']:>16}{fan['calls']:>18}")
    print(f"{'input tokens':<40}{solo['in']:>16}{fan['in']:>18}")
    print(f"{'output tokens (the generation grind)':<40}{solo['out']:>16}{fan['out']:>18}")
    print(f"{'total tokens':<40}{solo_total:>16}{fan_total:>18}")
    print(f"{'wall-clock seconds':<40}{solo['seconds']:>16.2f}{fan['seconds']:>18.2f}")
    print("-" * 74)
    print()

    # ---- the honest headline (offload), stated as measured facts -----------
    print("WHAT ALGERNON ACTUALLY DID (measured, not claimed):")
    print(f"  * The expensive orchestrator generated {solo['out']} output tokens by")
    print(f"    itself in SOLO. With Algernon it generated 0 — the cheap fleet")
    print(f"    produced those {fan['out']} output tokens instead. The grind moved off")
    print(f"    the orchestrator.")
    print(f"  * Biggest prompt one worker had to read: {fan['max_worker_in']} tokens")
    print(f"    (avg {fan['avg_worker_in']:.0f}). SOLO had to ingest all {solo['in']} at once.")
    print(f"    Each worker sees only its slice; the orchestrator never holds the")
    print(f"    whole job in one context.")
    print()
    print("THE HONEST TRADE-OFFS (no cherry-picking):")
    print(f"  * Total tokens fan-out vs solo: {_pct(fan_total, solo_total)} "
          f"({fan_total} vs {solo_total}).")
    print(f"    Fan-out normally spends MORE total tokens — each worker re-pays a")
    print(f"    little prompt overhead. You trade some total tokens for keeping the")
    print(f"    expensive mind free.")
    print(f"  * Wall-clock fan-out vs solo: {_pct(fan['seconds'], solo['seconds'])} "
          f"({fan['seconds']:.2f}s vs {solo['seconds']:.2f}s).")
    print(f"    Wall-clock only drops if your fleet runs requests in PARALLEL. A")
    print(f"    single local ollama with num_parallel=1 serializes them, so expect")
    print(f"    little/no speed win here — point Algernon at a real fleet (ollama")
    print(f"    OLLAMA_NUM_PARALLEL>1, multiple endpoints, or a hosted cheap tier)")
    print(f"    and the {fan['calls']} calls run concurrently.")
    print()
    print("Numbers vary slightly run-to-run (LLM nondeterminism); the pattern holds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
