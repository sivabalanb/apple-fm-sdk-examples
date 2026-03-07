"""
File Search Tool Example

Demonstrates two tools working together in one session:
  - FileSearchTool: searches for files matching a glob pattern under cwd
  - FileReaderTool: reads the text content of a given file path

Key concepts:
- Multiple fm.Tool subclasses registered in a single session
- Using pathlib for file system operations
- Handling ExceededContextWindowSizeError by recreating the session
"""

import pathlib

import FoundationModels as fm


class FileSearchTool(fm.Tool):
    """Searches the current working directory for files matching a glob pattern."""

    @fm.generable
    class Arguments:
        pattern: str
        """Glob pattern to search for, e.g. '**/*.py' or '*.txt'."""

    def __init__(self, search_root: pathlib.Path | None = None):
        super().__init__()
        self.search_root = search_root or pathlib.Path.cwd()

    @property
    def name(self) -> str:
        return "file_search"

    @property
    def description(self) -> str:
        return (
            "Searches for files matching a glob pattern under the working directory. "
            "Returns a list of matching file paths."
        )

    @property
    def arguments_schema(self):
        return self.Arguments.generation_schema()

    async def call(self, args: fm.GeneratedContent) -> str:
        pattern = args.pattern
        try:
            matches = sorted(self.search_root.glob(pattern))
            if not matches:
                return f"No files found matching pattern '{pattern}' under '{self.search_root}'."
            paths = [str(p) for p in matches[:50]]  # cap at 50 results
            result_lines = "\n".join(paths)
            return f"Found {len(paths)} file(s) matching '{pattern}':\n{result_lines}"
        except Exception as e:
            return f"Error searching for '{pattern}': {e}"


class FileReaderTool(fm.Tool):
    """Reads the text content of a file given its path."""

    @fm.generable
    class Arguments:
        file_path: str
        """Absolute or relative path to the file to read."""

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "file_reader"

    @property
    def description(self) -> str:
        return (
            "Reads and returns the text content of the specified file. "
            "Only works with plain text files."
        )

    @property
    def arguments_schema(self):
        return self.Arguments.generation_schema()

    async def call(self, args: fm.GeneratedContent) -> str:
        file_path = pathlib.Path(args.file_path)
        try:
            if not file_path.exists():
                return f"Error: file not found at '{file_path}'."
            if not file_path.is_file():
                return f"Error: '{file_path}' is not a file."
            content = file_path.read_text(encoding="utf-8", errors="replace")
            # Truncate very large files to avoid context overflow
            max_chars = 4000
            if len(content) > max_chars:
                content = content[:max_chars] + f"\n... [truncated at {max_chars} characters]"
            return f"Contents of '{file_path}':\n\n{content}"
        except PermissionError:
            return f"Error: permission denied reading '{file_path}'."
        except Exception as e:
            return f"Error reading '{file_path}': {e}"


def create_session(search_tool: FileSearchTool, reader_tool: FileReaderTool) -> fm.LanguageModelSession:
    """Create a new session with both file tools attached."""
    return fm.LanguageModelSession(
        model=fm.SystemLanguageModel.default,
        tools=[search_tool, reader_tool],
        instructions=(
            "You are a file system assistant. Use the file_search tool to find files "
            "and the file_reader tool to read their contents. Always report your findings clearly."
        ),
    )


async def main():
    search_root = pathlib.Path.cwd()
    search_tool = FileSearchTool(search_root=search_root)
    reader_tool = FileReaderTool()
    session = create_session(search_tool, reader_tool)

    questions = [
        "Find all Python files in the current directory.",
        "Find all .txt files here, then read the first one you find.",
        "Are there any README files? If so, show me the content.",
    ]

    for question in questions:
        print(f"\nQuestion: {question}")
        try:
            response = await session.respond(to=question)
            print(f"Answer: {response.content}")
        except fm.ExceededContextWindowSizeError:
            print("Context window exceeded — recreating session and retrying.")
            session = create_session(search_tool, reader_tool)
            try:
                response = await session.respond(to=question)
                print(f"Answer (after reset): {response.content}")
            except Exception as retry_err:
                print(f"Retry failed: {retry_err}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
