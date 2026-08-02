# Algernon MCP
<!-- mcp-name: io.github.sammyboi81/algernon -->

### *Orchestrate a fleet. Keep your mind.*

Algernon is an open-source
[Model Context Protocol](https://modelcontextprotocol.io) server that lets any
assistant — Claude, Codex, or any MCP client — **dispatch tightly-scoped
parallel sub-tasks to a fleet of cheap workers, collect the results, and stay
free to think.** Orchestrate a fleet, spend fewer tokens, keep the thread.

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

## Install in one command

```bash
python -m pip install algernon-mcp
```

The installed MCP command is `algernon`.

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
