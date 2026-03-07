"""
Code Review Agent Example

Demonstrates a code review workflow with two tools sharing a CodeReviewMemory
instance:
  - SnippetStorageTool: store, retrieve, and list code snippets
  - ReviewFeedbackTool: add review feedback, retrieve it, or get a summary

Three code examples are submitted for review across a multi-turn conversation.
Application memory (CodeReviewMemory) survives session resets caused by
ExceededContextWindowSizeError.

Key concepts:
- Domain-specific in-process memory shared across tools
- make_session() factory for clean session recreation
- Graceful ExceededContextWindowSizeError handling
"""

import datetime

import FoundationModels as fm


# ---------------------------------------------------------------------------
# Application memory
# ---------------------------------------------------------------------------

class CodeReviewMemory:
    """Stores code snippets and their review feedback in-process."""

    def __init__(self):
        self._snippets: dict[str, dict] = {}
        self._feedback: dict[str, list[dict]] = {}
        self._counter = 0

    # -- Snippets ------------------------------------------------------------

    def store_snippet(self, name: str, language: str, code: str) -> str:
        self._counter += 1
        snippet_id = f"SNIP-{self._counter:03d}"
        self._snippets[snippet_id] = {
            "id": snippet_id,
            "name": name,
            "language": language.lower(),
            "code": code,
            "stored_at": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        self._feedback[snippet_id] = []
        return snippet_id

    def retrieve_snippet(self, identifier: str) -> dict | None:
        # Try exact ID
        snippet = self._snippets.get(identifier.upper())
        if snippet is None:
            # Fall back to name search (case-insensitive)
            identifier_lower = identifier.lower()
            for s in self._snippets.values():
                if identifier_lower in s["name"].lower():
                    return s
        return snippet

    def list_snippets(self) -> list[dict]:
        return list(self._snippets.values())

    # -- Feedback ------------------------------------------------------------

    def add_feedback(self, snippet_id: str, category: str, comment: str, severity: str) -> str:
        snippet_id = snippet_id.upper()
        if snippet_id not in self._feedback:
            return f"No snippet with ID '{snippet_id}' found."
        feedback_entry = {
            "category": category.lower(),
            "comment": comment,
            "severity": severity.lower(),
            "added_at": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        self._feedback[snippet_id].append(feedback_entry)
        return f"Feedback added to {snippet_id}."

    def get_feedback(self, snippet_id: str) -> list[dict]:
        return self._feedback.get(snippet_id.upper(), [])

    def get_summary(self) -> dict:
        total_snippets = len(self._snippets)
        total_feedback = sum(len(fb) for fb in self._feedback.values())
        severity_counts: dict[str, int] = {}
        for feedbacks in self._feedback.values():
            for fb in feedbacks:
                sev = fb["severity"]
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
        snippets_reviewed = sum(1 for fb in self._feedback.values() if fb)
        return {
            "total_snippets": total_snippets,
            "snippets_reviewed": snippets_reviewed,
            "total_feedback_items": total_feedback,
            "severity_breakdown": severity_counts,
        }


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

class SnippetStorageTool(fm.Tool):
    """Stores, retrieves, and lists code snippets in the review session."""

    @fm.generable
    class Arguments:
        action: str
        """
        Action to perform. One of:
        - 'store'    -> save a new code snippet (requires name, language, code)
        - 'retrieve' -> fetch a snippet by ID or name (requires snippet_identifier)
        - 'list'     -> list all stored snippets
        """

        name: str
        """Human-readable name for the snippet. Required for action='store'."""

        language: str
        """Programming language, e.g. 'python', 'javascript'. Required for action='store'."""

        code: str
        """The source code to store. Required for action='store'."""

        snippet_identifier: str
        """Snippet ID (e.g. SNIP-001) or partial name. Required for action='retrieve'."""

    def __init__(self, memory: CodeReviewMemory):
        super().__init__()
        self.memory = memory

    @property
    def name(self) -> str:
        return "snippet_storage"

    @property
    def description(self) -> str:
        return (
            "Stores, retrieves, and lists code snippets for review. "
            "Use action='store' to save code, 'retrieve' to fetch it, and 'list' to see all snippets."
        )

    @property
    def arguments_schema(self):
        return self.Arguments.generation_schema()

    async def call(self, args: fm.GeneratedContent) -> str:
        action = (args.action or "").strip().lower()

        if action == "store":
            name = (args.name or "").strip()
            language = (args.language or "unknown").strip()
            code = (args.code or "").strip()
            if not name:
                return "Error: 'name' is required to store a snippet."
            if not code:
                return "Error: 'code' is required to store a snippet."
            snippet_id = self.memory.store_snippet(name, language, code)
            return (
                f"Snippet stored.\n"
                f"  ID:       {snippet_id}\n"
                f"  Name:     {name}\n"
                f"  Language: {language}\n"
                f"  Size:     {len(code)} characters"
            )

        elif action == "retrieve":
            identifier = (args.snippet_identifier or "").strip()
            if not identifier:
                return "Error: 'snippet_identifier' is required to retrieve a snippet."
            snippet = self.memory.retrieve_snippet(identifier)
            if snippet is None:
                return f"No snippet found matching '{identifier}'."
            return (
                f"Snippet [{snippet['id']}] — {snippet['name']} ({snippet['language']})\n"
                f"Stored at: {snippet['stored_at']}\n\n"
                f"```{snippet['language']}\n{snippet['code']}\n```"
            )

        elif action == "list":
            snippets = self.memory.list_snippets()
            if not snippets:
                return "No snippets stored yet."
            lines = [f"Stored snippets ({len(snippets)} total):"]
            for s in snippets:
                fb_count = len(self.memory.get_feedback(s["id"]))
                lines.append(
                    f"  [{s['id']}] {s['name']} ({s['language']}) — {fb_count} feedback item(s)"
                )
            return "\n".join(lines)

        else:
            return f"Unknown action '{action}'. Use 'store', 'retrieve', or 'list'."


class ReviewFeedbackTool(fm.Tool):
    """Adds review feedback to a snippet or retrieves existing feedback."""

    @fm.generable
    class Arguments:
        action: str
        """
        Action to perform. One of:
        - 'add'     -> add feedback to a snippet (requires snippet_id, category, comment, severity)
        - 'get'     -> retrieve all feedback for a snippet (requires snippet_id)
        - 'summary' -> get a summary of all review activity (no extra fields needed)
        """

        snippet_id: str
        """Snippet ID (e.g. SNIP-001). Required for action='add' and 'get'."""

        category: str
        """
        Feedback category. One of: 'security', 'performance', 'readability',
        'correctness', 'style', 'best_practice'. Required for action='add'.
        """

        comment: str
        """The review comment text. Required for action='add'."""

        severity: str
        """
        Severity level: 'critical', 'major', 'minor', 'info'.
        Required for action='add'.
        """

    def __init__(self, memory: CodeReviewMemory):
        super().__init__()
        self.memory = memory

    @property
    def name(self) -> str:
        return "review_feedback"

    @property
    def description(self) -> str:
        return (
            "Records and retrieves code review feedback. Use action='add' to leave a "
            "comment on a snippet, 'get' to see all feedback for a snippet, or "
            "'summary' for an overview of the entire review session."
        )

    @property
    def arguments_schema(self):
        return self.Arguments.generation_schema()

    async def call(self, args: fm.GeneratedContent) -> str:
        action = (args.action or "").strip().lower()

        if action == "add":
            snippet_id = (args.snippet_id or "").strip()
            category = (args.category or "general").strip()
            comment = (args.comment or "").strip()
            severity = (args.severity or "minor").strip()
            if not snippet_id:
                return "Error: 'snippet_id' is required to add feedback."
            if not comment:
                return "Error: 'comment' is required to add feedback."
            result = self.memory.add_feedback(snippet_id, category, comment, severity)
            return result

        elif action == "get":
            snippet_id = (args.snippet_id or "").strip().upper()
            if not snippet_id:
                return "Error: 'snippet_id' is required to retrieve feedback."
            feedback_list = self.memory.get_feedback(snippet_id)
            if not feedback_list:
                return f"No feedback recorded for snippet '{snippet_id}'."
            lines = [f"Feedback for {snippet_id} ({len(feedback_list)} item(s)):"]
            for i, fb in enumerate(feedback_list, start=1):
                lines.append(
                    f"\n  [{i}] [{fb['severity'].upper()}] {fb['category']}\n"
                    f"      {fb['comment']}"
                )
            return "\n".join(lines)

        elif action == "summary":
            summary = self.memory.get_summary()
            sev_lines = []
            for sev, count in sorted(summary["severity_breakdown"].items()):
                sev_lines.append(f"    {sev}: {count}")
            sev_text = "\n".join(sev_lines) if sev_lines else "    (none)"
            return (
                f"Code Review Session Summary:\n"
                f"  Snippets stored:       {summary['total_snippets']}\n"
                f"  Snippets with feedback:{summary['snippets_reviewed']}\n"
                f"  Total feedback items:  {summary['total_feedback_items']}\n"
                f"  Severity breakdown:\n{sev_text}"
            )

        else:
            return f"Unknown action '{action}'. Use 'add', 'get', or 'summary'."


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

def make_session(
    snippet_tool: SnippetStorageTool,
    feedback_tool: ReviewFeedbackTool,
) -> fm.LanguageModelSession:
    """Create (or recreate) a model session. Memory is held by the tools."""
    return fm.LanguageModelSession(
        model=fm.SystemLanguageModel.default,
        tools=[snippet_tool, feedback_tool],
        instructions=(
            "You are a senior code reviewer. Use the snippet_storage tool to store and "
            "retrieve code, and the review_feedback tool to record your analysis. "
            "For each snippet: identify security issues, performance concerns, and style "
            "improvements. Be specific and actionable in your feedback."
        ),
    )


# ---------------------------------------------------------------------------
# Code examples for review
# ---------------------------------------------------------------------------

AUTH_FUNCTION = """\
def authenticate_user(username, password):
    users = {"admin": "password123", "user1": "abc123"}
    if username in users and users[username] == password:
        return True
    return False
"""

IMPROVED_AUTH = """\
import hashlib
import secrets

USERS = {
    "admin": {
        "hash": hashlib.sha256(b"securepassword").hexdigest(),
        "salt": "randomsalt123"
    }
}

def authenticate_user(username: str, password: str) -> bool:
    user = USERS.get(username)
    if user is None:
        return False
    expected = hashlib.sha256(
        (password + user["salt"]).encode()
    ).hexdigest()
    return secrets.compare_digest(expected, user["hash"])
"""

API_HANDLER = """\
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/api/data", methods=["GET"])
def get_data():
    user_id = request.args.get("id")
    query = f"SELECT * FROM users WHERE id = {user_id}"
    # Execute query...
    return jsonify({"status": "ok", "query": query})
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    memory = CodeReviewMemory()
    snippet_tool = SnippetStorageTool(memory)
    feedback_tool = ReviewFeedbackTool(memory)
    session = make_session(snippet_tool, feedback_tool)

    print("=== Code Review Agent ===\n")

    async def ask(prompt: str) -> str:
        nonlocal session
        try:
            response = await session.respond(to=prompt)
            return response.content
        except fm.ExceededContextWindowSizeError:
            print("  [Context window exceeded — recreating session, memory preserved]")
            session = make_session(snippet_tool, feedback_tool)
            try:
                response = await session.respond(to=prompt)
                return response.content
            except Exception as retry_err:
                return f"[Retry failed: {retry_err}]"
        except Exception as e:
            return f"[Error: {e}]"

    # --- Step 1: Store and review the vulnerable auth function
    print("Step 1: Submitting basic auth function for review...")
    reply = await ask(
        f"Please store this Python snippet named 'basic_auth' and review it for security issues:\n\n{AUTH_FUNCTION}"
    )
    print(f"Agent: {reply}\n")

    # --- Step 2: Store and review the improved auth function
    print("Step 2: Submitting improved auth function...")
    reply = await ask(
        f"Store this improved auth snippet named 'improved_auth' and compare it to the first one:\n\n{IMPROVED_AUTH}"
    )
    print(f"Agent: {reply}\n")

    # --- Step 3: Store and review the SQL injection vulnerable API handler
    print("Step 3: Submitting Flask API handler with SQL injection risk...")
    reply = await ask(
        f"Store this Flask API handler named 'api_handler' and identify any critical vulnerabilities:\n\n{API_HANDLER}"
    )
    print(f"Agent: {reply}\n")

    # --- Step 4: Request a final summary
    print("Step 4: Requesting full review summary...")
    reply = await ask("Please give me a complete summary of all snippets reviewed and their feedback.")
    print(f"Agent: {reply}\n")

    # --- Final in-memory state (no model call needed)
    print("=== Final In-Memory Review State ===")
    summary = memory.get_summary()
    print(
        f"Snippets: {summary['total_snippets']} | "
        f"Reviewed: {summary['snippets_reviewed']} | "
        f"Total feedback: {summary['total_feedback_items']}"
    )
    if summary["severity_breakdown"]:
        print("Severity breakdown:")
        for sev, count in sorted(summary["severity_breakdown"].items()):
            print(f"  {sev}: {count}")
    print("\nAll stored snippets:")
    for s in memory.list_snippets():
        fb = memory.get_feedback(s["id"])
        print(f"  [{s['id']}] {s['name']} ({s['language']}) — {len(fb)} feedback item(s)")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
