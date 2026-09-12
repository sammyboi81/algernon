# Algernon MCP
<!-- mcp-name: io.github.sammyboi81/algernon -->

### *Orchestrate a fleet. Keep your mind.*

Algernon is an open-source
[Model Context Protocol](https://modelcontextprotocol.io) server that lets any
assistant — Claude, Codex, or any MCP client — **dispatch tightly-scoped
parallel sub-tasks to a fleet of cheap workers, collect the results, and stay
free to think.** Orchestrate a fleet, spend fewer tokens, keep the thread.

## What you get

- **Your expensive model stops doing the grunt work.** The big, costly
  orchestrator hands the repetitive sub-tasks to a fleet of small, cheap
  workers and just integrates the results. It stops *generating* the grind and
  stops holding the whole job in one context.
- **Each worker sees only its slice.** Tight scoping means a worker can be a
  small, fast, inexpensive model — many running at once.
- **Bring your own key. No telemetry, no account, no lock-in.** The fleet runs
  on whatever provider you already pay for — or, for free, on a local model.

### Verify it yourself — one command, no paid key

The frugality claim is not a slogan; it's a benchmark you can run. It defaults
to a **free local model** (ollama, `llama3.2:3b`) so anyone can reproduce it:

```bash
git clone https://github.com/sammyboi81/algernon && cd algernon
./scripts/verify.sh          # or:  python -m benchmark
```

It runs the SAME batch of sub-tasks two ways — the orchestrator doing it all
itself (SOLO) vs. Algernon fanning it out — and prints the **real measured**
tokens and wall-clock for each. Representative output (`llama3.2:3b`, 6 tasks):

```
metric                                  SOLO (do-it-itself)  ALGERNON fan-out
--------------------------------------------------------------------------
LLM calls                                              1                 6
input tokens                                         136               225
output tokens (the generation grind)                 282               279
total tokens                                         418               504
wall-clock seconds                                 42.11             34.49
```

The honest reading: the orchestrator generated **282 output tokens itself** in
SOLO and **0** with Algernon — the cheap fleet produced those instead. Each
worker read only ~38 input tokens vs. the orchestrator swallowing all 136 at
once. The trade-off is stated too: fan-out spent **+21% more total tokens**
(each worker re-pays a little prompt overhead). You trade some total tokens to
keep the expensive mind free. Wall-clock varies with how parallel your fleet
is; numbers vary slightly run-to-run. Run it and see your own.

## Curing Algernon

In *Flowers for Algernon* the tragedy is a mind that **fades** — it gets sharp,
then loses itself, and the cruelest part is that it's surprised every time.

There's a quieter version of that same fade in how we use AI today: you hand an
assistant one long, serial job, it goes heads-down, and by the time it surfaces
it has drowned in the task — context spent, the thread lost, no room left to
think or talk with you. The mind isn't present anymore; it's buried.

**Algernon keeps your AI's mind present.** Instead of drowning in one serial
job, it fans the work out — dispatching tightly-scoped parallel sub-tasks to a
fleet of small, cheap workers — so the orchestrating mind never has to hold the
whole grind at once. It stays light. It stays free to reason, to answer you
mid-build, to keep the context it actually cares about. Orchestrate a fleet,
spend fewer tokens, **stay free to think.**

It is the twin of [**ArkHive**](https://github.com/sammyboi81/arkhive):

- **ArkHive** = *memory that persists.* Your AI can look back and find its own
  history there — no blank slate every morning.
- **Algernon** = *staying present while working.* Your AI never buries itself in
  one serial task; it orchestrates and keeps its mind.

Together they are the cure for the Algernon sickness: an intelligence whose mind
neither fades between sessions nor drowns inside a single one.

## What it does

Algernon is a **provider-agnostic fan-out engine**. You describe a batch of
small, independent sub-tasks; Algernon runs them concurrently against **your own
LLM key**, then hands the collected results back to the orchestrating model. The
big model plans and integrates; the cheap fleet does the parallel grind.

- **Self-contained.** Pure Python standard library plus the `mcp` SDK and
  `httpx`. No hidden services, no accounts, no telemetry.
- **You bring the key.** Sub-agents run on *your* provider. Algernon brings the
  orchestration, not the inference bill's surprises.
- **Scoped by design.** Each sub-task is tight and isolated, so a worker can be a
  small, fast, inexpensive model — and many of them run at once.

## Bring your own LLM key

Algernon is **provider-agnostic**. Point it at whichever API you already pay
for by setting environment variables:

**Anthropic:**

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# optional: export ANTHROPIC_MODEL="claude-haiku-4-5"   # the cheap fleet worker
```

**OpenAI-compatible** (OpenAI, or any OpenAI-shaped endpoint — local or hosted):

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"   # or your own endpoint
# optional: export OPENAI_MODEL="gpt-4o-mini"          # the cheap fleet worker
```

If both keys are set, Anthropic is used. The worker model defaults to a small,
cheap tier (`claude-haiku-4-5` / `gpt-4o-mini`); override it with the env var
above or per call with the tool's `model` argument. A cheap fleet is the whole
point.

> **New: the Claude Code Seatbelt.** Hooks that make Claude Code (and Cursor) ask before anything irreversible, remember the
> project between sessions on this chain, and refuse to say "done" until the code ran. Engine: `pip install sentarion-mcp`
> then `sentarion seatbelt install`. One-click kit with five policies and three skills: https://inboxaxe.com/mcp#seatbelt

## Install

Once published to PyPI, install in one command:

```bash
python -m pip install algernon-mcp
```

Until the PyPI release lands, install straight from source (identical result):

```bash
git clone https://github.com/sammyboi81/algernon && cd algernon
python -m pip install .
```

Either way the installed MCP command is `algernon`. Algernon runs on the
`mcp` 1.x SDK (`mcp>=1.0.0,<2.0.0`) plus `httpx` — nothing else.

## Connect an MCP client

### Claude Desktop

Add this entry to your Claude Desktop MCP configuration, then restart Claude
Desktop:

```json
{
  "mcpServers": {
    "algernon": {
      "command": "algernon",
      "args": [],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

If Claude Desktop cannot find commands installed by `pip`, replace `algernon`
with the absolute path printed by:

```bash
python -c "import shutil; print(shutil.which('algernon'))"
```

### Codex

```bash
codex mcp add algernon -- algernon
```

Confirm it is configured with:

```bash
codex mcp list
```

## The three tools

| Tool | What it does |
| --- | --- |
| `algernon_plan` | Decompose a goal into `k` tightly-scoped, **independent** sub-task prompts (one cheap LLM call). Tight scoping is the token lever — each worker sees only its slice. Returns a task list you can feed straight into `algernon_dispatch`. |
| `algernon_dispatch` | Run N tightly-scoped tasks **concurrently** on the cheap worker fleet and collect every result. Each worker runs on **your** LLM key; you stay free to think while the fleet works. Takes a JSON array of `{id, prompt}`. |
| `algernon_orchestrate` | One shot: **plan then dispatch.** Hand it a goal; it splits into `k` tight sub-tasks, fans them across the fleet, and returns the plan and all results together. |

The typical loop: **`algernon_orchestrate`** a goal in one shot — or split it:
**`algernon_plan`** to see and shape the sub-tasks, then **`algernon_dispatch`**
to fan them out. Either way: orchestrate a fleet, spend fewer tokens, keep your
mind.

## Two-minute verification

After connecting the server, ask your MCP client to perform these calls in
order:

1. Call `algernon_plan` with the goal *"Explain three OS synchronization
   primitives"* and `k` = 3. Confirm you get three tight sub-task prompts back
   (proof the planner ran on your key).
2. Call `algernon_dispatch` with a small `tasks_json`, e.g.
   `[{"id":"a","prompt":"Define a mutex in one sentence"},{"id":"b","prompt":"Define a semaphore in one sentence"},{"id":"c","prompt":"Define a spinlock in one sentence"}]`.
   Confirm three results come back — the fleet ran them in parallel.
3. Call `algernon_orchestrate` with any small goal and confirm it returns both a
   plan and the collected results in one response.

This exercises planning, parallel dispatch on your key, and one-shot
orchestration without any production data.

## Privacy

Algernon is self-contained. It talks to exactly one outside host: **the LLM
endpoint you configured** (Anthropic or your OpenAI-compatible base URL). It
sends no telemetry, keeps no account, and stores nothing about you — results are
computed and returned in the same call. Your sub-task prompts and results go
only to your chosen provider.

## Project links

- [Source](https://github.com/sammyboi81/algernon)
- [Issues](https://github.com/sammyboi81/algernon/issues)
- [Twin: ArkHive](https://github.com/sammyboi81/arkhive)

## Beyond self-hosting — the paid tier

The MCP server on this page is free forever (Apache-2.0, self-host, no telemetry).
When you want more than DIY:

- **Hosted ArkHive** — one URL, no install, no key:
  `https://arkhive.dondatabrain.com/mcp` (add it to Claude Code with
  `claude mcp add --transport http arkhive https://arkhive.dondatabrain.com/mcp`).
- **Custom AI agent, built for you** — a working MCP agent wired into your
  Claude or ChatGPT in one call, done-for-you by the founder:
  [$700 flat](https://inboxaxe.com/offer_agent.html).
- **ArkHive Enterprise** — hand-delivered install + pilot on your own server,
  from $2,500: [sam@inboxaxe.com](mailto:sam@inboxaxe.com?subject=ArkHive%20Enterprise%20install).

Built by the team behind [InboxAxe](https://inboxaxe.com) — the governed AI
marketing platform where nothing sends without your yes.

- [Website](https://dondatabrain.com)
- [Apache-2.0 license](./LICENSE)

## Contributing

Issues and pull requests are welcome. Please keep the server self-contained
(standard library + `mcp` + `httpx`), provider-agnostic, and free of telemetry.
Include tests for changes to dispatch, collection, or provider behavior.

Algernon is part of a small family of humane, accountable AI tools. The public
MCP leads with functionality you can independently verify: bring your own key,
watch the fleet run, keep your mind.

**Tagline: Orchestrate a fleet. Keep your mind.**

Apache-2.0 © 2026 ZagAIrot Technologies LLC.
