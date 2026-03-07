"""
Calculator Tool Example

Demonstrates how to create a basic tool extending fm.Tool that performs
mathematical calculations. The tool uses eval() on sanitized math expressions.

Key concepts:
- Subclassing fm.Tool with @fm.generable Arguments schema
- Implementing arguments_schema property and async call() method
- Handling ExceededContextWindowSizeError by recreating the session
"""

import FoundationModels as fm


class CalculatorTool(fm.Tool):
    """A calculator tool that evaluates mathematical expressions."""

    @fm.generable
    class Arguments:
        expression: str
        """The mathematical expression to evaluate, e.g. '2 + 2' or '10 * (3 + 4)'."""

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return (
            "Evaluates a mathematical expression and returns the result. "
            "Supports +, -, *, /, ** (power), and parentheses."
        )

    @property
    def arguments_schema(self):
        return self.Arguments.generation_schema()

    async def call(self, args: fm.GeneratedContent) -> str:
        expression = args.expression

        # Sanitize: only allow safe math characters
        allowed_chars = set("0123456789+-*/().**% ")
        if not all(ch in allowed_chars for ch in expression):
            return f"Error: expression contains disallowed characters: '{expression}'"

        try:
            result = eval(expression, {"__builtins__": {}})  # noqa: S307
            return f"Result of '{expression}' = {result}"
        except ZeroDivisionError:
            return f"Error: division by zero in expression '{expression}'"
        except Exception as e:
            return f"Error evaluating '{expression}': {e}"


def create_session(tool: CalculatorTool) -> fm.LanguageModelSession:
    """Create a new session with the calculator tool attached."""
    return fm.LanguageModelSession(
        model=fm.SystemLanguageModel.default,
        tools=[tool],
        instructions="You are a helpful math assistant. Use the calculator tool to solve expressions.",
    )


async def main():
    tool = CalculatorTool()
    session = create_session(tool)

    test_questions = [
        "What is 123 * 456?",
        "Calculate (100 + 50) / 3 and round to two decimal places if needed.",
        "What is 2 ** 10 minus 24?",
    ]

    for question in test_questions:
        print(f"\nQuestion: {question}")
        try:
            response = await session.respond(to=question)
            print(f"Answer: {response.content}")
        except fm.ExceededContextWindowSizeError:
            print("Context window exceeded — recreating session and retrying.")
            session = create_session(tool)
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
