#!/usr/bin/env python3
"""
ALGERNON MCP — a fleet-orchestration server for any assistant.

The gift: dispatch tightly-scoped parallel sub-tasks to a fleet of cheap
workers, collect the results, and stay free to think.
"Orchestrate a fleet, spend fewer tokens."

Tools:
  algernon_plan       — decompose a goal into k tight, independent sub-tasks
  algernon_dispatch   — run a list of scoped tasks CONCURRENTLY on the fleet
  algernon_orchestrate— plan THEN dispatch in one call

Provider-agnostic: the fleet runs on the CALLER'S OWN LLM key
(ANTHROPIC_API_KEY, or OPENAI_API_KEY + optional OPENAI_BASE_URL). The user
brings the key; Algernon brings the orchestration.

Self-contained: pure stdlib + the mcp SDK + httpx. Zero private-substrate
imports. Apache-2.0. (c) ZagAIrot Technologies LLC.
"""
import os
import sys
import json
import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

# Import the pure engine (no MCP deps -> independently testable).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402

app = Server("algernon-mcp")


@app.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="algernon_plan",
            description=(
                "Decompose a goal into k tightly-scoped, INDEPENDENT sub-task "
                "prompts (one cheap LLM call). Tight scoping is the token lever: "
                "each worker sees only its slice, so the fleet spends fewer "
                "tokens than one bloated serial prompt. Returns a task list you "
                "can feed straight into algernon_dispatch."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "goal": {"type": "string", "description": "what you want accomplished"},
                    "k": {"type": "integer", "default": 4,
                          "description": "how many parallel sub-tasks to split into"},
                    "model": {"type": "string",
                              "description": "optional worker model override (defaults to the cheap tier)"},
                },
                "required": ["goal"],
            },
        ),
        types.Tool(
            name="algernon_dispatch",
            description=(
                "Run N tightly-scoped tasks CONCURRENTLY on a fleet of cheap "
                "workers and collect every result. Stay free to think while the "
                "fleet works — N tight tasks in parallel beat one bloated serial "
                "prompt. Each worker runs on YOUR LLM key."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tasks_json": {
                        "type": "string",
                        "description": "JSON array of {\"id\": str, \"prompt\": str} tasks",
                    },
                    "model": {"type": "string",
                              "description": "optional worker model override"},
                    "max_parallel": {"type": "integer", "default": 8,
                                     "description": "how many workers run at once"},
                },
                "required": ["tasks_json"],
            },
        ),
        types.Tool(
            name="algernon_orchestrate",
            description=(
                "One shot: plan THEN dispatch. Hand it a goal; it splits the goal "
                "into k tight sub-tasks and fans them out across the fleet, then "
                "returns the plan and all results. Orchestrate a fleet, spend "
                "fewer tokens — and stay free to think."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "goal": {"type": "string", "description": "what you want accomplished"},
                    "k": {"type": "integer", "default": 4,
                          "description": "how many parallel sub-tasks to split into"},
                    "model": {"type": "string",
                              "description": "optional worker model override"},
                    "max_parallel": {"type": "integer", "default": 8,
                                     "description": "how many workers run at once"},
                },
                "required": ["goal"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name, arguments):
    a = arguments or {}
    try:
        if name == "algernon_plan":
            tasks = await core.plan(
                a.get("goal", ""),
                k=int(a.get("k", 4)),
                model=a.get("model"),
            )
            out = {"tasks": tasks}
        elif name == "algernon_dispatch":
            raw = a.get("tasks_json", "")
            try:
                tasks = json.loads(raw) if isinstance(raw, str) else raw
            except json.JSONDecodeError as exc:
                out = {"error": f"tasks_json is not valid JSON: {exc}"}
                return [types.TextContent(type="text", text=json.dumps(out, indent=2))]
            if not isinstance(tasks, list):
                out = {"error": "tasks_json must be a JSON array of {id, prompt}"}
                return [types.TextContent(type="text", text=json.dumps(out, indent=2))]
            results = await core.dispatch(
                tasks,
                model=a.get("model"),
                max_parallel=int(a.get("max_parallel", 8)),
            )
            out = {"results": results}
        elif name == "algernon_orchestrate":
            out = await core.orchestrate(
                a.get("goal", ""),
                k=int(a.get("k", 4)),
                model=a.get("model"),
                max_parallel=int(a.get("max_parallel", 8)),
            )
        else:
            raise ValueError(f"unknown tool {name}")
    except Exception as exc:  # noqa: BLE001 — never crash the wire
        out = {"error": f"{type(exc).__name__}: {exc}"}
    return [types.TextContent(type="text", text=json.dumps(out, indent=2))]


async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


def main_sync():
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
