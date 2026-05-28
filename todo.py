from fastmcp import FastMCP
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
import json

mcp = FastMCP("todo_mcp")

class Task:
    def __init__(self, id: int, title: str, description: str = ""):
        self.id = id
        self.title = title
        self.description = description
        self.completed = False
        self.failed = False
        self.fail_reason: Optional[str] = None
        self.created_at = datetime.now().isoformat()
        self.completed_at: Optional[str] = None

_todo_list: dict[int, Task] = {}
_next_id = 1
_current_goal = ""

def _reset_state():
    global _todo_list, _next_id, _current_goal
    _todo_list = {}
    _next_id = 1
    _current_goal = ""

class SetupInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    goal: str = Field(..., description="The overall goal for this session", min_length=1, max_length=500)
    tasks: list[str] = Field(..., description="List of task titles to complete in order", min_items=1, max_items=50)

class AddTaskInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(..., description="Task title", min_length=1, max_length=200)
    description: Optional[str] = Field(default="", description="Optional task description")

class CompleteTaskInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    task_id: int = Field(..., description="ID of the task to mark as completed", ge=1)

class UpdateGoalInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    goal: str = Field(..., description="New goal description", min_length=1, max_length=500)

class FailTaskInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    task_id: int = Field(..., description="ID of the task that failed", ge=1)
    reason: str = Field(..., description="Why the task failed and what went wrong", min_length=1, max_length=500)

@mcp.tool(
    annotations={
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False,
    }
)
def todo_setup(params: SetupInput) -> str:
    """Initialize the todo list with a goal and tasks.

    THIS MUST BE CALLED FIRST. It resets all state and creates the checklist.

    WORKFLOW RULE — Awareness Loop (execute → assess → recover → list):
    1. Call todo_setup once to create the list
    2. Call todo_list to see the first task
    3. Execute that task using your own abilities
    4. ANALYZE the result carefully — did it actually succeed?
    5a. If success → call todo_complete to tick it off
    5b. If failure → call todo_fail with the reason, then call todo_add to insert a recovery step
    6. Call todo_list again — ALWAYS go back to the checklist after every task
    7. Repeat step 3→6 until todo_list says ALL TASKS COMPLETED
    8. Only then provide the final answer to the user

    AWARENESS: If a task fails, don't pretend it succeeded. Mark it failed, create a new
    recovery task, and continue. The plan is dynamic — adapt as you go.

    VIOLATION: If you skip todo_list between tasks or answer before all done, you fail.

    Args:
        params (SetupInput): Contains:
            - goal (str): The overall goal for this session
            - tasks (list[str]): Ordered list of task titles to complete

    Returns:
        str: Summary of the setup with goal and task count
    """
    global _current_goal
    _reset_state()
    _current_goal = params.goal
    global _next_id
    for title in params.tasks:
        _todo_list[_next_id] = Task(_next_id, title)
        _next_id += 1
    return (
        f"CHECKLIST CREATED\n"
        f"Goal: {params.goal}\n"
        f"Total tasks: {len(params.tasks)}\n\n"
        f"Pending:\n{_task_summary('pending')}\n\n"
        f"NEXT: Call todo_list to see your first task."
    )

def _task_summary(filter_mode: str):
    if filter_mode == "done":
        tasks = [t for t in _todo_list.values() if t.completed and not t.failed]
    elif filter_mode == "failed":
        tasks = [t for t in _todo_list.values() if t.failed]
    elif filter_mode == "pending":
        tasks = [t for t in _todo_list.values() if not t.completed and not t.failed]
    else:
        tasks = []
    if not tasks:
        return "None"
    lines = []
    for t in tasks:
        if t.failed:
            lines.append(f"  #{t.id} [FAILED] {t.title}\n         Reason: {t.fail_reason}")
        elif t.completed:
            lines.append(f"  #{t.id} [DONE] {t.title}")
        else:
            desc = f" - {t.description}" if t.description else ""
            lines.append(f"  #{t.id} [PENDING] {t.title}{desc}")
    return "\n".join(lines)

@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def todo_list() -> str:
    """Check the current checklist and see what to do next.

    THIS IS YOUR CHECKPOINT — You MUST call this:
    - After todo_setup to see the first task
    - After EVERY todo_complete or todo_fail to see what's next
    - Whenever you need to re-check what remains

    AWARENESS LOOP — You must assess task results honestly:
    setup → list → execute → ANAlYZE →
      (success) → complete → list → ...
      (failure) → fail → add recovery step → list → ...

    If you try to answer the user without todo_list showing ALL TASKS COMPLETED,
    you are skipping tasks and that is not allowed.

    FAILED TASKS: These are shown separately. You must decide what to do:
    1. Add a recovery task with todo_add and retry
    2. Update the goal with todo_update_goal to change direction
    The system will not auto-recover — you must take action.

    Returns:
        str: Current checklist status with pending, failed, and completed tasks
    """
    if not _todo_list:
        return "No checklist yet. Call todo_setup first."
    pending = _task_summary("pending")
    done = _task_summary("done")
    failed = _task_summary("failed")
    total = len(_todo_list)
    done_count = sum(1 for t in _todo_list.values() if t.completed and not t.failed)
    failed_count = sum(1 for t in _todo_list.values() if t.failed)
    pending_count = total - done_count - failed_count

    lines = [f"=== CHECKLIST ===", f"Goal: {_current_goal}", f"Progress: {done_count}/{total}", ""]
    if done_count > 0:
        lines.append(f"Completed ({done_count}):")
        lines.append(done)
        lines.append("")
    if failed_count > 0:
        lines.append(f"FAILED ({failed_count}) — requires your decision:")
        lines.append(failed)
        lines.append("")
        lines.append("ACTION REQUIRED: One or more tasks have failed. Analyze why and decide:")
        lines.append("  - If retryable: call todo_add to insert a recovery task")
        lines.append("  - If skipable: call todo_add with 'Skip: {task}' to mark it bypassed")
        lines.append("  - If plan is wrong: call todo_update_goal to recalibrate")
        lines.append("")
    if pending_count > 0:
        lines.append(f"Pending ({pending_count}):")
        lines.append(pending)
        lines.append("")
        lines.append("INSTRUCTION: Execute the next pending task now. After finishing, call todo_complete or todo_fail, then call todo_list again.")
    if pending_count == 0 and failed_count == 0:
        lines.append("ALL TASKS COMPLETED! You may now provide the final answer to the user.")
    return "\n".join(lines)

@mcp.tool(
    annotations={
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    }
)
def todo_complete(params: CompleteTaskInput) -> str:
    """Mark a task as completed on the checklist.

    After calling this, you MUST immediately call todo_list to check what's next.
    Do NOT skip the checklist — the loop is: execute → complete → list.

    Args:
        params (CompleteTaskInput): Contains:
            - task_id (int): ID of the task to mark completed

    Returns:
        str: Confirmation message
    """
    task = _todo_list.get(params.task_id)
    if not task:
        return f"Error: Task #{params.task_id} not found. Call todo_list to see valid IDs."
    if task.completed:
        return f"Task #{params.task_id} '{task.title}' was already completed. Call todo_list to check what remains."
    task.completed = True
    task.completed_at = datetime.now().isoformat()
    remaining = sum(1 for t in _todo_list.values() if not t.completed and not t.failed)
    if remaining == 0:
        return f"[TICK] Task #{params.task_id} '{task.title}' done. All tasks complete! Call todo_list to confirm."
    return f"[TICK] Task #{params.task_id} '{task.title}' done. {remaining} task(s) left. Call todo_list NOW to see what's next."

@mcp.tool(
    annotations={
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    }
)
def todo_fail(params: FailTaskInput) -> str:
    """Mark a task as failed with a reason for the failure.

    AWARENESS — This is how you handle tasks that didn't work:
    When a task's result is unacceptable (wrong output, error, blocked),
    do NOT complete it. Mark it failed and adapt the plan.

    After calling this, you MUST:
    1. Analyze WHY it failed
    2. Decide what to do next:
       - If it can be retried differently → call todo_add to insert a new recovery task
       - If it can be skipped → call todo_add with 'Skip: {title}' to create a bypass task
       - If the entire plan is off → call todo_update_goal to recalibrate
    3. Call todo_list to see the updated picture

    WRONG: Completing a task that actually failed (pretending works).
    RIGHT: Failing honestly and adding a recovery step.

    Args:
        params (FailTaskInput): Contains:
            - task_id (int): ID of the task that failed
            - reason (str): What went wrong and why

    Returns:
        str: Confirmation with guidance on next steps
    """
    task = _todo_list.get(params.task_id)
    if not task:
        return f"Error: Task #{params.task_id} not found. Call todo_list to see valid IDs."
    if task.failed:
        return f"Task #{params.task_id} '{task.title}' was already marked failed. Call todo_list to assess."
    if task.completed:
        return f"Task #{params.task_id} '{task.title}' was already completed. If you must redo it, call todo_add to create a new task."
    task.failed = True
    task.fail_reason = params.reason
    remaining = sum(1 for t in _todo_list.values() if not t.completed and not t.failed)
    return (
        f"[FAIL] Task #{params.task_id} '{task.title}' marked as failed.\n"
        f"  Reason: {params.reason}\n"
        f"  {remaining} pending task(s) remain.\n\n"
        f"ANALYZE AND DECIDE: Should you add a recovery task via todo_add, "
        f"skip this and continue, or update the goal? Call todo_list to assess."
    )

@mcp.tool(
    annotations={
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    }
)
def todo_add(params: AddTaskInput) -> str:
    """Add a new task to the checklist mid-session.

    After adding, call todo_list to see the updated checklist.

    Args:
        params (AddTaskInput): Contains:
            - title (str): Task title
            - description (Optional[str]): Optional description

    Returns:
        str: Confirmation with the new task's ID
    """
    global _next_id
    task = Task(_next_id, params.title, params.description or "")
    _todo_list[_next_id] = task
    _next_id += 1
    return f"Added task #{task.id}: {task.title}. Call todo_list to see updated checklist."

@mcp.tool(
    annotations={
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False,
    }
)
def todo_update_goal(params: UpdateGoalInput) -> str:
    """Update the session goal.

    Args:
        params (UpdateGoalInput): Contains:
            - goal (str): New goal description

    Returns:
        str: Confirmation
    """
    global _current_goal
    _current_goal = params.goal
    return f"Goal updated to: {_current_goal}"

@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def todo_next() -> str:
    """Get the single next pending task description.

    Shorthand to see what to do right now without the full list.

    Returns:
        str: The next pending task
    """
    pending = [t for t in _todo_list.values() if not t.completed and not t.failed]
    if not pending:
        return "All tasks completed!"
    task = pending[0]
    desc = f"\n   Description: {task.description}" if task.description else ""
    return f"Next task (#{task.id}): {task.title}{desc}"

if __name__ == "__main__":
    mcp.run()
