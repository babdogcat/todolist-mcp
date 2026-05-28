# Todo MCP — Awareness-Driven Task Loop for AI Agents

> A **local task management tool** that enforces an honest, failure-aware task execution loop for LLM-powered agents. Built with Python and FastMCP, runs directly on your machine.

[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB)](https://python.org)
[![FastMCP](https://img.shields.io/badge/FastMCP-powered-00a86b)](https://github.com/jlowin/fastmcp)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

## Overview

Todo MCP provides a structured **task management loop** for AI agents (Claude, GPT, Gemini, etc.). Instead of asking an LLM to plan and execute everything in one shot, this tool enforces a **sequential awareness loop** that runs locally:

```
setup → list → execute → ANALYZE →
  (success) → complete → list → ...
  (failure) → fail → add recovery step → list → ...
  ... → ALL DONE → answer
```

The agent must honestly assess each task result, handle failures dynamically, and check the checklist after every step — no skipping, no pretending, no early answers.

## Keywords

task management, todo list, local AI tools, LLM task loop, Python task manager, FastMCP, agent workflow, task orchestration, AI task runner, sequential task execution, failure-aware agent, LLM task management, AI workflow automation, local Python tool

## Features

- **Awareness Loop** — Forces the agent to analyze results and adapt before moving on
- **Honest Failure Handling** — `todo_fail` captures reasons and prompts recovery decisions
- **Dynamic Task Management** — Add tasks mid-session, update goals on the fly
- **Token Efficiency** — State lives server-side; compact summaries replace re-stating the entire plan
- **No Client Enforcement Needed** — Tool descriptions and return values act as behavioral instructions to the LLM

## Tools

| Tool | Purpose |
|---|---|
| `todo_setup` | Initialize a goal and ordered task list (resets state) |
| `todo_list` | Show pending, failed, and completed tasks — the central checkpoint |
| `todo_complete` | Mark a task completed |
| `todo_fail` | Mark a task failed with a reason; prompts recovery decision |
| `todo_add` | Add a new task mid-session (e.g. a recovery step) |
| `todo_update_goal` | Change the session goal |
| `todo_next` | Quick peek at the next pending task |

## Quick Start (Run Local)

### 1. Get the code

```bash
git clone https://github.com/your-username/todo-mcp.git
cd todo-mcp
```

Or [download the ZIP](https://github.com/babdogcat/todolist-mcp/archive/refs/heads/main.zip) and extract it.

### 2. Install & run

```bash
pip install fastmcp
python todo.py
```

The tool runs locally on your machine — no cloud services, no API keys, no server setup.

## Requirements

- Python 3.11+
- `fastmcp` (`pip install fastmcp`)

## How It Works

This tool uses **docstring-driven instruction enforcement** at the protocol level. Every tool's description is written as a direct command to the LLM, not just documentation.

### The Mechanism

1. `todo_setup` teaches the full awareness loop with "MUST" language and a "VIOLATION" warning
2. `todo_list` demands the agent call it after *every* task and shows failed tasks separately
3. `todo_complete` reminds the agent to check the list next
4. `todo_fail` forces a conscious adaptation decision
5. `todo_list` declares **ALL TASKS COMPLETED** — the only signal to answer

### Token Efficiency

This tool reduces token usage by acting as an **external scratchpad**:

- State lives on the server, not repeated in conversation context
- Compact status lines replace verbose re-stating of the plan
- No backtracking overhead — the next task is always explicitly listed
- Early failure detection saves expensive rollback cost

## Usage

### Standard Path

1. `todo_setup` — Initialize with a goal and task list
2. `todo_list` — See the first task
3. Execute the work using your own abilities
4. Assess the result honestly
5. `todo_complete` — Tick it off
6. `todo_list` — Check what's next; repeat from step 3
7. When `todo_list` returns **ALL TASKS COMPLETED** — provide final answer

### Failure Path

1. `todo_setup` — Initialize
2. `todo_list` — See the first task
3. Execute — result is unacceptable
4. `todo_fail` — Mark it failed with the reason
5. `todo_add` — Insert a recovery task
6. `todo_list` — Check updated checklist
7. Continue until **ALL TASKS COMPLETED**

## Awareness: Honest or Pretending?

This tool enforces the checklist loop and the failure structure. It cannot verify the LLM actually did the work. A dishonest agent can call `todo_complete` on an unexecuted task. The awareness feature provides the **structure for honest adaptation** — but still depends on the LLM's willingness to self-critique.

For best results, combine this tool with **real action tools** (file I/O, API calls, command execution). When side effects are visible, pretending becomes detectable, and awareness genuinely improves execution quality.

## Project Structure

```
todo-mcp/
├── todo.py         # Main implementation (FastMCP)
├── README.md       # Full documentation
└── ReadMeSEO.md    # SEO-optimized overview
```

## Example Prompt
### Example 1
```
Goal: Analyze my startup's runway and suggest 3 cost cuts.
Tasks:
1. Pull current burn rate from the financial spreadsheet
2. Calculate months of runway remaining
3. Identify 3 largest non-headcount expenses
4. Suggest specific cuts with estimated savings
5. Format everything into a memo
```

### Example 2
```
## WorkFlow
- Set up WorkFlow
- Write World Building for anime isekai (after complete return in chat)
- Write Character put in world (after complete return in chat)
- Write Plot of story (after complete return in chat)
```

The agent works through each task one at a time, checking the checklist after every completion.

## Why This Approach Works

LLMs treat tool descriptions and return values as actionable instructions. By crafting every message as a command for what to call *next*, the tool creates a behavioral loop without any client-side enforcement. The agent quite literally cannot "see" a path to answering until the checklist is drained.
