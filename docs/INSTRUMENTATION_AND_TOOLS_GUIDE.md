# Instrumentation & Tools Guide

## Part 1: Instrumentation & Performance Profiling

Apple FM SDK has **no built-in instrumentation**. Use `time.perf_counter()` and custom metrics.

### Key Metrics

| Metric | What It Measures | How |
|--------|-----------------|-----|
| **Latency** | Total generation time | `time.perf_counter()` |
| **Time-to-First-Token** | Streaming start delay | `perf_counter()` on first chunk |
| **Throughput** | Tokens per second | `tokens / elapsed` |
| **Memory** | RSS growth | `psutil.Process().memory_info()` |

### Why `time.perf_counter()`?

Use `time.perf_counter()`, not `time.time()`:
- `time.perf_counter()` — High-resolution monotonic clock (never jumps backwards)
- `time.time()` — Wall-clock (can jump due to system adjustments)

### Basic Latency Measurement

```python
import time
import apple_fm_sdk as fm

start = time.perf_counter()
response = await session.respond(prompt)
elapsed = time.perf_counter() - start

tokens = len(response) // 4  # ~4 chars per token
throughput = tokens / elapsed
print(f"Latency: {elapsed:.3f}s | Throughput: {throughput:.1f} tok/s")
```

### Time-to-First-Token (Streaming)

```python
start = time.perf_counter()
first_token_time = None

async for chunk in session.stream_response(prompt):
    if first_token_time is None:
        first_token_time = time.perf_counter() - start
        print(f"TTFT: {first_token_time*1000:.0f}ms")
```

### LatencyMetrics + PerformanceProfiler Pattern

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class LatencyMetrics:
    total_time: float
    first_token_time: Optional[float] = None
    character_count: int = 0
    tokens_per_second: float = 0.0

    @property
    def estimated_tokens(self) -> int:
        return max(1, self.character_count // 4)

class PerformanceProfiler:
    def __init__(self):
        self.measurements: list[LatencyMetrics] = []

    def record(self, metrics: LatencyMetrics) -> None:
        self.measurements.append(metrics)

    def summary(self) -> dict:
        times = [m.total_time for m in self.measurements]
        return {
            "count": len(times),
            "avg_latency_s": sum(times) / len(times),
            "min_latency_s": min(times),
            "max_latency_s": max(times),
        }
```

See `02-streaming/instrumentation_and_profiling.py` for the complete example.

### SLO Monitoring Pattern

```python
class SLOMonitor:
    def __init__(self, p95_threshold_s=2.0):
        self.p95_threshold = p95_threshold_s
        self.latencies = []

    def record(self, latency_s: float):
        self.latencies.append(latency_s)

    def check_slo(self):
        if not self.latencies:
            return
        sorted_l = sorted(self.latencies)
        p95 = sorted_l[int(len(sorted_l) * 0.95)]
        if p95 > self.p95_threshold:
            print(f"SLO violation: p95={p95:.3f}s > {self.p95_threshold}s")
        else:
            print(f"SLO met: p95={p95:.3f}s")
```

---

## Part 2: Tools — Custom Capabilities

Apple FM SDK does **NOT** have "custom adapters." It has **Tools** — Python functions the model can call.

### Tool Anatomy

```python
import apple_fm_sdk as fm

class WeatherTool(fm.Tool):
    name = "WeatherTool"
    description = "Get current weather for a location"

    @fm.generable("Weather query")
    class Arguments:
        location: str = fm.guide("City name")
        unit: str = fm.guide(anyOf=["celsius", "fahrenheit"])

    @property
    def arguments_schema(self) -> fm.GenerationSchema:
        return self.Arguments.generation_schema()

    async def call(self, args: fm.GeneratedContent) -> str:
        location = args.location
        unit = args.unit
        # Fetch real data or return mock
        return f"{location}: 22°{unit[0].upper()}"

# Register with session
session = fm.LanguageModelSession(
    model=model,
    tools=[WeatherTool()]
)
response = await session.respond("What's the weather in Chicago?")
```

### Tool Lifecycle

```
User prompt → Model decides to use tool → System calls tool.call()
→ Tool returns string → Model uses result → Final response to user
```

### Stateful Tools (Adapter-Like Pattern)

```python
class DatabaseTool(fm.Tool):
    def __init__(self, connection_string: str):
        super().__init__()
        self.connection_string = connection_string
        self._db = None

    async def call(self, args: fm.GeneratedContent) -> str:
        if self._db is None:
            self._db = connect(self.connection_string)
        query = args.query
        return str(self._db.execute(query))
```

### Tool Guidelines

| Do | Don't |
|----|-------|
| Return clear strings | Return raw objects |
| Handle errors gracefully | Let exceptions bubble up |
| Keep calls fast | Make slow blocking calls |
| Validate inputs | Assume inputs are safe |
| Log tool calls | Silent failures |

### Multi-Tool Sessions

```python
session = fm.LanguageModelSession(
    model=model,
    tools=[CalculatorTool(), FileWriterTool(), WeatherTool()]
)
# Model picks the right tool automatically
response = await session.respond("Calculate 100+200, then tell me Chicago weather")
```

## See Also

- `04-tool-calling/calculator_tool.py` — Basic tool example
- `04-tool-calling/multi_tool_agent.py` — Multiple tools, model-driven selection
- `04-tool-calling/stateful_agent.py` — Stateful tool with memory
- `docs/STATEFUL_PATTERNS.md` — Multi-turn workflows with tool state
