"""
Stateful Agent Example

Demonstrates application-level memory that survives session resets.
Two tools share a single TaskMemory instance:
  - TaskManagerTool: add, complete, and list tasks
  - ContextTool: get a summary of the current task state

Session resets (due to ExceededContextWindowSizeError) do NOT lose task data
because memory lives in Python objects, not in the model's context window.

Key concepts:
- Shared mutable state across multiple tools
- create_session() helper for clean session recreation
- Application memory surviving context window resets
- Concise conversation prompts to avoid hitting context limits
"""

import datetime

import FoundationModels as fm


# ---------------------------------------------------------------------------
# Application memory — lives entirely in Python, not in the model session
# ---------------------------------------------------------------------------

class TaskMemory:
    """In-process store for tasks. Survives session resets."""

    def __init__(self):
        self._tasks: dict[str, dict] = {}
        self._counter = 0

    def add_task(self, title: str, due_date: str, priority: str) -> str:
        self._counter += 1
        task_id = f"TASK-{self._counter:03d}"
        self._tasks[task_id] = {
            "id": task_id,
            "title": title,
            "due_date": due_date,
            "priority": priority.lower(),
            "status": "pending",
            "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "completed_at": None,
        }
        return task_id

    def complete_task(self, identifier: str) -> tuple[bool, str]:
        """Mark a task done by ID or title (case-insensitive partial match)."""
        # Try exact ID match first
        task = self._tasks.get(identifier.upper())
        if task is None:
            # Fall back to title search
            identifier_lower = identifier.lower()
            for t in self._tasks.values():
                if identifier_lower in t["title"].lower():
                    task = t
                    break
        if task is None:
            return False, f"No task found matching '{identifier}'."
        if task["status"] == "done":
            return True, f"Task '{task['title']}' ({task['id']}) is already marked done."
        task["status"] = "done"
        task["completed_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        return True, f"Task '{task['title']}' ({task['id']}) marked as done."

    def list_tasks(self, status_filter: str | None = None) -> list[dict]:
        tasks = list(self._tasks.values())
        if status_filter:
            tasks = [t for t in tasks if t["status"] == status_filter.lower()]
        return sorted(tasks, key=lambda t: (t["priority"] != "high", t["due_date"]))

    def get_task_info(self, identifier: str) -> dict | None:
        task = self._tasks.get(identifier.upper())
        if task is None:
            identifier_lower = identifier.lower()
            for t in self._tasks.values():
                if identifier_lower in t["title"].lower():
                    return t
        return task

    def get_summary(self) -> dict:
        all_tasks = list(self._tasks.values())
        pending = [t for t in all_tasks if t["status"] == "pending"]
        done = [t for t in all_tasks if t["status"] == "done"]
        high = [t for t in pending if t["priority"] == "high"]
        return {
            "total": len(all_tasks),
            "pending": len(pending),
            "done": len(done),
            "high_priority_pending": len(high),
        }


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

class TaskManagerTool(fm.Tool):
    """
    Manages tasks: create a new task, mark a task as complete, or list tasks.
    """

    @fm.generable
    class Arguments:
        action: str
        """
        Action to perform. One of:
        - 'add'      -> create a new task (requires title, due_date, priority)
        - 'complete' -> mark a task done (requires task_id_or_title)
        - 'list'     -> list tasks, optionally filtered (optional status_filter)
        """

        title: str
        """Task title. Required when action='add'."""

        due_date: str
        """Due date string, e.g. 'March 15'. Required when action='add'."""

        priority: str
        """Priority level: 'high', 'medium', or 'low'. Required when action='add'."""

        task_id_or_title: str
        """Task ID (e.g. TASK-001) or partial title. Required when action='complete'."""

        status_filter: str
        """Optional filter for action='list': 'pending' or 'done'. Leave empty for all."""

    def __init__(self, memory: TaskMemory):
        super().__init__()
        self.memory = memory

    @property
    def name(self) -> str:
        return "task_manager"

    @property
    def description(self) -> str:
        return (
            "Manages a task list. Use action='add' to create tasks, "
            "'complete' to mark them done, and 'list' to view tasks."
        )

    @property
    def arguments_schema(self):
        return self.Arguments.generation_schema()

    async def call(self, args: fm.GeneratedContent) -> str:
        action = (args.action or "").strip().lower()

        if action == "add":
            title = (args.title or "").strip()
            due_date = (args.due_date or "").strip()
            priority = (args.priority or "medium").strip()
            if not title:
                return "Error: 'title' is required when adding a task."
            task_id = self.memory.add_task(title, due_date, priority)
            return (
                f"Task created successfully.\n"
                f"  ID:       {task_id}\n"
                f"  Title:    {title}\n"
                f"  Due:      {due_date}\n"
                f"  Priority: {priority}"
            )

        elif action == "complete":
            identifier = (args.task_id_or_title or "").strip()
            if not identifier:
                return "Error: 'task_id_or_title' is required when completing a task."
            success, message = self.memory.complete_task(identifier)
            return message

        elif action == "list":
            status_filter = (args.status_filter or "").strip() or None
            tasks = self.memory.list_tasks(status_filter=status_filter)
            if not tasks:
                label = f" with status '{status_filter}'" if status_filter else ""
                return f"No tasks found{label}."
            lines = []
            for t in tasks:
                status_icon = "✓" if t["status"] == "done" else "○"
                lines.append(
                    f"  {status_icon} [{t['id']}] {t['title']} "
                    f"(due: {t['due_date']}, priority: {t['priority']}, status: {t['status']})"
                )
            header = f"Tasks ({len(tasks)} total"
            if status_filter:
                header += f", filter: {status_filter}"
            header += "):"
            return header + "\n" + "\n".join(lines)

        else:
            return f"Unknown action '{action}'. Use 'add', 'complete', or 'list'."


class ContextTool(fm.Tool):
    """Returns a high-level summary of the current task state."""

    @fm.generable
    class Arguments:
        include_details: str
        """
        Whether to include the full task list in the summary.
        Pass 'yes' to include all tasks, or 'no' for counts only.
        """

    def __init__(self, memory: TaskMemory):
        super().__init__()
        self.memory = memory

    @property
    def name(self) -> str:
        return "context_tool"

    @property
    def description(self) -> str:
        return (
            "Returns a summary of current task counts and optionally the full task list. "
            "Useful for giving the user an overview of their workload."
        )

    @property
    def arguments_schema(self):
        return self.Arguments.generation_schema()

    async def call(self, args: fm.GeneratedContent) -> str:
        summary = self.memory.get_summary()
        include_details = (args.include_details or "no").strip().lower()

        lines = [
            "Task Summary:",
            f"  Total tasks:           {summary['total']}",
            f"  Pending:               {summary['pending']}",
            f"  Done:                  {summary['done']}",
            f"  High-priority pending: {summary['high_priority_pending']}",
        ]

        if include_details == "yes":
            all_tasks = self.memory.list_tasks()
            if all_tasks:
                lines.append("\nAll tasks:")
                for t in all_tasks:
                    status_icon = "✓" if t["status"] == "done" else "○"
                    lines.append(
                        f"  {status_icon} [{t['id']}] {t['title']} "
                        f"(due: {t['due_date']}, priority: {t['priority']})"
                    )

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

def create_session(task_tool: TaskManagerTool, context_tool: ContextTool) -> fm.LanguageModelSession:
    """Create (or recreate) a session. Memory is held by the tools, not the session."""
    return fm.LanguageModelSession(
        model=fm.SystemLanguageModel.default,
        tools=[task_tool, context_tool],
        instructions=(
            "You are a task management assistant. Use the task_manager tool to add, "
            "complete, or list tasks. Use the context_tool when the user asks for a "
            "summary or overview. Be concise and confirm each action clearly."
        ),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    # Shared application memory — outlives any single session
    memory = TaskMemory()
    task_tool = TaskManagerTool(memory)
    context_tool = ContextTool(memory)
    session = create_session(task_tool, context_tool)

    conversation_flow = [
        "Create a task: project proposal, due March 15, high priority",
        "Create a task: review API docs, due March 20, medium priority",
        "Create a task: presentation slides, due March 22, high priority",
        "List all my tasks",
        "Mark the project proposal as done",
        "Show me a summary of my tasks",
    ]

    print("=== Stateful Task Manager Agent ===\n")
    print(f"Application memory persists across session resets.\n")

    for i, prompt in enumerate(conversation_flow, start=1):
        print(f"[Turn {i}] User: {prompt}")
        try:
            response = await session.respond(to=prompt)
            print(f"[Turn {i}] Agent: {response.content}\n")
        except fm.ExceededContextWindowSizeError:
            print(f"[Turn {i}] Context window exceeded — recreating session (memory preserved).")
            session = create_session(task_tool, context_tool)
            try:
                response = await session.respond(to=prompt)
                print(f"[Turn {i}] Agent (after reset): {response.content}\n")
            except Exception as retry_err:
                print(f"[Turn {i}] Retry failed: {retry_err}\n")
        except Exception as e:
            print(f"[Turn {i}] Error: {e}\n")

    # Final state straight from memory (no model needed)
    print("\n=== Final In-Memory State ===")
    summary = memory.get_summary()
    print(f"Total: {summary['total']} | Pending: {summary['pending']} | Done: {summary['done']}")
    for task in memory.list_tasks():
        status = "DONE" if task["status"] == "done" else "PENDING"
        print(f"  [{task['id']}] {task['title']} — {status} (due: {task['due_date']}, priority: {task['priority']})")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
