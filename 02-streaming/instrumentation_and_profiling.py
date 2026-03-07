"""
02 — Instrumentation & Performance Profiling
Demonstrates: Measuring latency, throughput, and performance patterns.

Apple FM SDK doesn't include built-in instrumentation, so we'll build our own
monitoring using time.perf_counter() (high-resolution clock) and custom metrics.

Key metrics to measure:
- Latency: How long does a generation take?
- Time-to-first-token: How long until streaming starts?
- Throughput: Tokens per second
- Memory: Does session memory grow over time?
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Optional

import apple_fm_sdk as fm


@dataclass
class LatencyMetrics:
    """Container for latency measurements."""
    total_time: float  # Total wall-clock time
    first_token_time: Optional[float] = None  # Time to first token (streaming only)
    character_count: int = 0  # Output length
    prompt_length: int = 0  # Input length
    tokens_per_second: float = 0.0  # Estimated throughput
    tokens_generated: int = 0  # Rough token count

    @property
    def estimated_tokens(self) -> int:
        """Rough estimate: 4 characters ≈ 1 token."""
        return max(1, self.character_count // 4)

    def __str__(self) -> str:
        return (
            f"Latency: {self.total_time:.3f}s | "
            f"Output: {self.character_count} chars (~{self.estimated_tokens} tokens) | "
            f"Throughput: {self.tokens_per_second:.1f} tok/s"
        )


class PerformanceProfiler:
    """Measure and track generation performance."""

    def __init__(self):
        self.measurements: list[LatencyMetrics] = []

    def record(self, metrics: LatencyMetrics) -> None:
        """Record a measurement."""
        self.measurements.append(metrics)

    def summary(self) -> dict:
        """Compute aggregate statistics."""
        if not self.measurements:
            return {}

        times = [m.total_time for m in self.measurements]
        tokens = [m.estimated_tokens for m in self.measurements]
        throughputs = [m.tokens_per_second for m in self.measurements]

        return {
            "count": len(self.measurements),
            "min_latency_s": min(times),
            "max_latency_s": max(times),
            "avg_latency_s": sum(times) / len(times),
            "median_latency_s": sorted(times)[len(times) // 2],
            "total_tokens": sum(tokens),
            "avg_throughput": sum(throughputs) / len(throughputs) if throughputs else 0,
            "total_time_s": sum(times),
        }

    def print_summary(self) -> None:
        """Print performance summary."""
        stats = self.summary()
        if not stats:
            print("No measurements recorded")
            return

        print("\n" + "=" * 70)
        print("PERFORMANCE SUMMARY")
        print("=" * 70)
        print(f"Total requests:     {stats['count']}")
        print(f"Total time:         {stats['total_time_s']:.2f}s")
        print(f"Total tokens:       {stats['total_tokens']}")
        print(f"\nLatency Statistics:")
        print(f"  Min:              {stats['min_latency_s']:.3f}s")
        print(f"  Max:              {stats['max_latency_s']:.3f}s")
        print(f"  Average:          {stats['avg_latency_s']:.3f}s")
        print(f"  Median:           {stats['median_latency_s']:.3f}s")
        print(f"\nThroughput:")
        print(f"  Average:          {stats['avg_throughput']:.1f} tokens/s")
        print("=" * 70)


async def measure_latency(
    session: fm.LanguageModelSession,
    prompt: str,
    description: str = "",
) -> LatencyMetrics:
    """Measure latency of a single generation."""

    if description:
        print(f"\n[{description}]")

    # High-resolution clock for accurate timing
    start = time.perf_counter()

    try:
        response = await session.respond(prompt)

        elapsed = time.perf_counter() - start

        # Estimate tokens (rough: 4 chars ≈ 1 token)
        char_count = len(response)
        token_count = max(1, char_count // 4)
        throughput = token_count / elapsed if elapsed > 0 else 0

        metrics = LatencyMetrics(
            total_time=elapsed,
            character_count=char_count,
            prompt_length=len(prompt),
            tokens_per_second=throughput,
            tokens_generated=token_count,
        )

        print(f"  {metrics}")
        return metrics

    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"  Failed after {elapsed:.3f}s: {type(e).__name__}")
        raise


async def measure_streaming_latency(
    session: fm.LanguageModelSession,
    prompt: str,
    description: str = "",
) -> LatencyMetrics:
    """Measure streaming latency including time-to-first-token."""

    if description:
        print(f"\n[{description}]")

    start = time.perf_counter()
    first_token_time: Optional[float] = None
    char_count = 0

    try:
        async for chunk in session.stream_response(prompt):
            # Record time to first chunk
            if first_token_time is None:
                first_token_time = time.perf_counter() - start

            char_count = len(chunk)  # Cumulative

        total_time = time.perf_counter() - start

        # Estimate tokens
        token_count = max(1, char_count // 4)
        throughput = token_count / total_time if total_time > 0 else 0

        metrics = LatencyMetrics(
            total_time=total_time,
            first_token_time=first_token_time,
            character_count=char_count,
            prompt_length=len(prompt),
            tokens_per_second=throughput,
            tokens_generated=token_count,
        )

        ttft = f"{first_token_time*1000:.0f}ms" if first_token_time else "N/A"
        print(f"  {metrics} | Time-to-first-token: {ttft}")
        return metrics

    except Exception as e:
        total_time = time.perf_counter() - start
        print(f"  Failed after {total_time:.3f}s: {type(e).__name__}")
        raise


async def main():
    # Check availability
    model = fm.SystemLanguageModel()
    is_available, reason = model.is_available()

    print("=" * 70)
    print("  INSTRUMENTATION & PERFORMANCE PROFILING")
    print("  Measure latency, throughput, and performance patterns")
    print("=" * 70)

    if not is_available:
        print(f"Model not available: {reason}")
        return

    # Create profiler
    profiler = PerformanceProfiler()

    def new_session():
        """Create a fresh session to avoid context window buildup."""
        return fm.LanguageModelSession(
            instructions="You are helpful and concise.",
            model=model,
        )

    # Test 1: Basic latency measurement
    print("\n" + "=" * 70)
    print("TEST 1: Basic Latency Measurement")
    print("=" * 70)

    prompts = [
        ("Short response", "What is Python in one sentence?"),
        ("Medium response", "Explain machine learning briefly"),
        ("Longer response", "List 5 benefits of cloud computing"),
    ]

    for desc, prompt in prompts:
        session = new_session()
        try:
            metrics = await measure_latency(session, prompt, desc)
            profiler.record(metrics)
        except fm.ExceededContextWindowSizeError:
            print(f"  [{desc}] Context window exceeded — skipping")

    # Test 2: Streaming latency (time-to-first-token)
    print("\n" + "=" * 70)
    print("TEST 2: Streaming Latency & Time-to-First-Token")
    print("=" * 70)

    stream_prompts = [
        ("Quick stream", "What is AI?"),
        ("Longer stream", "Explain neural networks briefly"),
    ]

    for desc, prompt in stream_prompts:
        session = new_session()
        try:
            metrics = await measure_streaming_latency(session, prompt, desc)
            profiler.record(metrics)
        except fm.ExceededContextWindowSizeError:
            print(f"  [{desc}] Context window exceeded — skipping")

    # Test 3: Throughput under multiple rounds
    print("\n" + "=" * 70)
    print("TEST 3: Throughput Over Multiple Rounds")
    print("=" * 70)

    print("\nProcessing 5 sequential requests...")
    for i in range(1, 6):
        session = new_session()
        try:
            metrics = await measure_latency(
                session,
                f"Tell me a fact about technology",
                f"Round {i}",
            )
            profiler.record(metrics)
        except fm.ExceededContextWindowSizeError:
            print(f"  [Round {i}] Context window exceeded — skipping")

    # Print summary
    profiler.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
