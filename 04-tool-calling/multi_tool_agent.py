"""
Multi-Tool Agent Example

Demonstrates an agent with three distinct tools where the model decides which
tool to use based on the user's question:
  - DateTimeTool: returns current date/time info
  - UnitConverterTool: converts temperature, distance, or weight
  - TextAnalyzerTool: counts words, characters, and sentences in text

Key concepts:
- Model autonomously selecting the appropriate tool per request
- Structured Arguments with enum-like string fields for conversion type
- Handling ExceededContextWindowSizeError by recreating the session
"""

import datetime
import re

import FoundationModels as fm


class DateTimeTool(fm.Tool):
    """Returns current date and time information."""

    @fm.generable
    class Arguments:
        format: str
        """
        Desired output format. One of: 'date', 'time', 'datetime', 'weekday', 'all'.
        - 'date'     -> YYYY-MM-DD
        - 'time'     -> HH:MM:SS
        - 'datetime' -> YYYY-MM-DD HH:MM:SS
        - 'weekday'  -> day name, e.g. 'Monday'
        - 'all'      -> all of the above
        """

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "datetime_tool"

    @property
    def description(self) -> str:
        return (
            "Returns the current date, time, or both in the requested format. "
            "Use format='all' for a full breakdown."
        )

    @property
    def arguments_schema(self):
        return self.Arguments.generation_schema()

    async def call(self, args: fm.GeneratedContent) -> str:
        now = datetime.datetime.now()
        fmt = (args.format or "all").strip().lower()

        if fmt == "date":
            return f"Today's date: {now.strftime('%Y-%m-%d')}"
        elif fmt == "time":
            return f"Current time: {now.strftime('%H:%M:%S')}"
        elif fmt == "datetime":
            return f"Current datetime: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        elif fmt == "weekday":
            return f"Today is: {now.strftime('%A')}"
        else:  # 'all' or unrecognized
            return (
                f"Date: {now.strftime('%Y-%m-%d')}\n"
                f"Time: {now.strftime('%H:%M:%S')}\n"
                f"Weekday: {now.strftime('%A')}\n"
                f"Full: {now.strftime('%Y-%m-%d %H:%M:%S')}"
            )


class UnitConverterTool(fm.Tool):
    """Converts values between units for temperature, distance, and weight."""

    @fm.generable
    class Arguments:
        conversion_type: str
        """
        Type of conversion. One of:
        'celsius_to_fahrenheit', 'fahrenheit_to_celsius', 'celsius_to_kelvin',
        'km_to_miles', 'miles_to_km', 'meters_to_feet', 'feet_to_meters',
        'kg_to_pounds', 'pounds_to_kg', 'grams_to_ounces', 'ounces_to_grams'.
        """

        value: float
        """The numeric value to convert."""

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "unit_converter"

    @property
    def description(self) -> str:
        return (
            "Converts a numeric value between units. Supports temperature (Celsius, "
            "Fahrenheit, Kelvin), distance (km, miles, meters, feet), and weight "
            "(kg, pounds, grams, ounces)."
        )

    @property
    def arguments_schema(self):
        return self.Arguments.generation_schema()

    async def call(self, args: fm.GeneratedContent) -> str:
        conversion_type = (args.conversion_type or "").strip().lower()
        try:
            value = float(args.value)
        except (TypeError, ValueError):
            return "Error: 'value' must be a numeric number."

        conversions = {
            "celsius_to_fahrenheit": (lambda v: v * 9 / 5 + 32, "{v}°C = {r:.2f}°F"),
            "fahrenheit_to_celsius": (lambda v: (v - 32) * 5 / 9, "{v}°F = {r:.2f}°C"),
            "celsius_to_kelvin":     (lambda v: v + 273.15,        "{v}°C = {r:.2f} K"),
            "km_to_miles":           (lambda v: v * 0.621371,      "{v} km = {r:.4f} miles"),
            "miles_to_km":           (lambda v: v * 1.60934,       "{v} miles = {r:.4f} km"),
            "meters_to_feet":        (lambda v: v * 3.28084,       "{v} m = {r:.4f} ft"),
            "feet_to_meters":        (lambda v: v / 3.28084,       "{v} ft = {r:.4f} m"),
            "kg_to_pounds":          (lambda v: v * 2.20462,       "{v} kg = {r:.4f} lbs"),
            "pounds_to_kg":          (lambda v: v / 2.20462,       "{v} lbs = {r:.4f} kg"),
            "grams_to_ounces":       (lambda v: v * 0.035274,      "{v} g = {r:.4f} oz"),
            "ounces_to_grams":       (lambda v: v / 0.035274,      "{v} oz = {r:.4f} g"),
        }

        if conversion_type not in conversions:
            supported = ", ".join(conversions.keys())
            return f"Unknown conversion type '{conversion_type}'. Supported: {supported}"

        fn, template = conversions[conversion_type]
        result = fn(value)
        return template.format(v=value, r=result)


class TextAnalyzerTool(fm.Tool):
    """Analyzes text and returns word, character, and sentence counts."""

    @fm.generable
    class Arguments:
        text: str
        """The text to analyze."""

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "text_analyzer"

    @property
    def description(self) -> str:
        return (
            "Analyzes a block of text and returns statistics: word count, "
            "character count (with and without spaces), and sentence count."
        )

    @property
    def arguments_schema(self):
        return self.Arguments.generation_schema()

    async def call(self, args: fm.GeneratedContent) -> str:
        text = args.text or ""
        if not text.strip():
            return "Error: no text provided to analyze."

        word_count = len(text.split())
        char_count_with_spaces = len(text)
        char_count_no_spaces = len(text.replace(" ", ""))
        # Sentences end with . ! or ?
        sentences = re.split(r"[.!?]+", text.strip())
        sentence_count = sum(1 for s in sentences if s.strip())

        # Most common word (case-insensitive, stripped of punctuation)
        words = re.findall(r"[a-zA-Z']+", text.lower())
        freq: dict[str, int] = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        most_common = max(freq, key=freq.get) if freq else "N/A"
        most_common_count = freq.get(most_common, 0)

        return (
            f"Text Analysis Results:\n"
            f"  Words:                     {word_count}\n"
            f"  Characters (with spaces):  {char_count_with_spaces}\n"
            f"  Characters (no spaces):    {char_count_no_spaces}\n"
            f"  Sentences:                 {sentence_count}\n"
            f"  Most common word:          '{most_common}' ({most_common_count} times)"
        )


def create_session(
    datetime_tool: DateTimeTool,
    converter_tool: UnitConverterTool,
    analyzer_tool: TextAnalyzerTool,
) -> fm.LanguageModelSession:
    """Create a new session with all three tools attached."""
    return fm.LanguageModelSession(
        model=fm.SystemLanguageModel.default,
        tools=[datetime_tool, converter_tool, analyzer_tool],
        instructions=(
            "You are a versatile assistant with three tools: a date/time tool, "
            "a unit converter, and a text analyzer. Choose the right tool based on "
            "the user's request and explain the result clearly."
        ),
    )


async def main():
    datetime_tool = DateTimeTool()
    converter_tool = UnitConverterTool()
    analyzer_tool = TextAnalyzerTool()
    session = create_session(datetime_tool, converter_tool, analyzer_tool)

    questions = [
        "What day of the week is it today?",
        "Convert 100 degrees Celsius to Fahrenheit.",
        "Convert 26.2 miles to kilometers.",
        "Analyze this text: 'The quick brown fox jumps over the lazy dog. It was a sunny day!'",
        "How many kilograms is 150 pounds?",
        "What is the current date and time?",
    ]

    for question in questions:
        print(f"\nQuestion: {question}")
        try:
            response = await session.respond(to=question)
            print(f"Answer: {response.content}")
        except fm.ExceededContextWindowSizeError:
            print("Context window exceeded — recreating session and retrying.")
            session = create_session(datetime_tool, converter_tool, analyzer_tool)
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
