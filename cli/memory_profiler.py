"""
Memory profiling utilities for debugging memory leaks in Tech Spec Agent.
"""

import tracemalloc
import gc
import sys
from typing import Optional


# Global flag to track if tracemalloc is running
_tracking_enabled = False


def log_memory_snapshot(label: str, top_n: int = 10):
    """
    Log current memory usage and top memory consumers.

    Args:
        label: Description of current execution point
        top_n: Number of top memory allocations to display
    """
    global _tracking_enabled

    if not _tracking_enabled:
        print(f"[MEMORY WARNING] Tracking not enabled, skipping snapshot: {label}", flush=True)
        return

    try:
        # Force garbage collection to get accurate reading
        gc.collect()

        # Get current memory usage
        current, peak = tracemalloc.get_traced_memory()

        print(f"\n{'='*70}", flush=True)
        print(f"[MEMORY SNAPSHOT] {label}", flush=True)
        print(f"{'='*70}", flush=True)
        print(f"Current: {current / 1024 / 1024:>10.1f} MB", flush=True)
        print(f"Peak:    {peak / 1024 / 1024:>10.1f} MB", flush=True)

        # Show top memory allocations
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')[:top_n]

        print(f"\nTop {top_n} memory allocations:", flush=True)
        print(f"{'Size (MB)':<12} {'Count':<10} Location", flush=True)
        print("-" * 70, flush=True)

        for stat in top_stats:
            size_mb = stat.size / 1024 / 1024
            print(f"{size_mb:<12.2f} {stat.count:<10} {stat}", flush=True)

        print(f"{'='*70}\n", flush=True)

    except Exception as e:
        print(f"[MEMORY ERROR] Failed to log snapshot '{label}': {e}", flush=True)
        import traceback
        traceback.print_exc()


def start_memory_tracking():
    """Initialize memory tracking."""
    global _tracking_enabled

    try:
        # Check if already running
        if tracemalloc.is_tracing():
            print("[MEMORY] Tracking already active", flush=True)
            _tracking_enabled = True
            return

        # Start tracking
        tracemalloc.start()
        _tracking_enabled = True
        print("[MEMORY] Tracking started successfully", flush=True)

        # Immediate test snapshot
        current, peak = tracemalloc.get_traced_memory()
        print(f"[MEMORY] Initial memory: {current / 1024 / 1024:.1f} MB", flush=True)

    except Exception as e:
        print(f"[MEMORY ERROR] Failed to start tracking: {e}", flush=True)
        import traceback
        traceback.print_exc()
        _tracking_enabled = False


def stop_memory_tracking():
    """Stop memory tracking and show final stats."""
    global _tracking_enabled

    if not _tracking_enabled:
        print("[MEMORY WARNING] Tracking was not enabled, nothing to stop", flush=True)
        return

    try:
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        _tracking_enabled = False

        print(f"\n[MEMORY] Tracking stopped", flush=True)
        print(f"  Final: {current / 1024 / 1024:.1f} MB", flush=True)
        print(f"  Peak:  {peak / 1024 / 1024:.1f} MB", flush=True)

    except Exception as e:
        print(f"[MEMORY ERROR] Failed to stop tracking: {e}", flush=True)
        import traceback
        traceback.print_exc()


# Module load test
print("[MEMORY PROFILER] Module loaded successfully", flush=True)
