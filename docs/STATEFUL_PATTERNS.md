# Stateful Patterns: Sessions with Tool Calling

How to build multi-turn workflows where session context and application state evolve together.

## The Core Pattern

```python
# 1. Define application state
class TaskMemory:
    def __init__(self):
        self.tasks: dict = {}

    def add_task(self, title, due, priority):
        task_id = f"task_{len(self.tasks) + 1}"
        self.tasks[task_id] = {"title": title, "due": due, "priority": priority, "status": "pending"}
        return task_id

# 2. Tool that modifies state
class TaskManagerTool(fm.Tool):
    def __init__(self, memory: TaskMemory):
        super().__init__()
        self.memory = memory

    async def call(self, args) -> str:
        # Modifies self.memory — persists across turns
        task_id = self.memory.add_task(args.title, args.due_date, args.priority)
        return f"Task created: {task_id}"

# 3. Session + stateful tool
memory = TaskMemory()
session = fm.LanguageModelSession(tools=[TaskManagerTool(memory)], model=model)

# 4. Multi-turn — BOTH session context AND memory accumulate
for user_input in conversation:
    response = await session.respond(user_input)
```

## What Evolves

### Session Context
`LanguageModelSession` maintains full conversation history — user messages and assistant responses accumulate, and the model references prior turns.

### Application State
Tools modify external data structures. Subsequent turns can query that data.

## Handling Context Window Overflow

Session history grows with each turn. When it overflows, recreate the session — the tool's memory is preserved because tools hold a reference to the memory object, not the session.

```python
def create_session(memory: TaskMemory) -> fm.LanguageModelSession:
    return fm.LanguageModelSession(
        instructions="You are a task assistant. Use TaskManager tool.",
        model=model,
        tools=[TaskManagerTool(memory)],
    )

memory = TaskMemory()
session = create_session(memory)

for user_input in conversation:
    try:
        response = await session.respond(user_input)
    except fm.ExceededContextWindowSizeError:
        # Memory survives — only session context is reset
        session = create_session(memory)
        response = await session.respond(user_input)
```

## Design Patterns

### Accumulation
State grows with each turn:
```python
memory.add_snippet(id, code)     # Turn 1
memory.add_snippet(id2, code2)   # Turn 2
all_snippets = memory.list()     # Turn 3 — sees both
```

### Lookup
Tools retrieve previously stored data:
```python
async def call(self, args) -> str:
    prior = self.memory.get_snippet(args.snippet_id)  # From a prior turn
    return f"Found: {prior}"
```

### State-Based Decisions
Agent behavior changes based on accumulated state:
```python
async def call(self, args) -> str:
    summary = self.memory.get_summary()
    if summary["pending_count"] > 5:
        return "You have many tasks — consider prioritizing."
    return self.memory.list_tasks()
```

## Common Pitfalls

### State Not Validated
```python
# Bad
item = self.memory.items[args.id]  # KeyError if missing

# Good
if args.id not in self.memory.items:
    return f"Item '{args.id}' not found"
item = self.memory.items[args.id]
```

### Forgetting State is Temporary
```python
# Memory is in-process — lost when program exits
# Persist if you need to survive restarts:
with open("state.json", "w") as f:
    json.dump(memory.to_dict(), f)
```

### Vague Instructions
```python
# Bad
session = fm.LanguageModelSession(instructions="Help the user")

# Good — tell the model about its tools
session = fm.LanguageModelSession(
    instructions=(
        "Use the TaskManager tool to create, list, and complete tasks. "
        "Be concise and confirm each action."
    ),
    tools=[task_tool]
)
```

## Performance Notes

- Single-threaded: one request at a time (hardware constraint)
- Session context grows with turns → slightly more tokens per request
- In-memory state is fast with no per-token cost
- Persist state to disk/DB for workflows that span restarts

## See Also

- `04-tool-calling/stateful_agent.py` — Task manager example (6-turn workflow)
- `04-tool-calling/code_review_agent.py` — Code review with snippet accumulation
- `04-tool-calling/multi_tool_agent.py` — Multiple tools, simpler state
- `docs/INSTRUMENTATION_AND_TOOLS_GUIDE.md` — Tool architecture reference
