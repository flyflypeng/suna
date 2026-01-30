import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
import argparse

LOG_FILE = "metrics_logs.jsonl" # Assuming run from root or adjusted path

def load_logs():
    logs = []
    if not os.path.exists(LOG_FILE):
        print(f"No log file found at {LOG_FILE}")
        return []

    with open(LOG_FILE, "r") as f:
        for line in f:
            try:
                logs.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return logs

def analyze_tools(logs):
    # Tools handled by specific analyzers (Context, Memory) should be excluded here
    excluded_tools = {"create_tasks", "update_tasks", "view_tasks", "complete", "manage_core_memory"}
    
    tool_stats = defaultdict(lambda: {"count": 0, "total_duration": 0, "errors": 0})

    for log in logs:
        if log["event_type"] == "tool_execution":
            data = log["data"]
            name = data.get("tool_name", "unknown")
            
            if name in excluded_tools:
                continue

            duration = data.get("duration_ms", 0)
            success = data.get("success", True)

            tool_stats[name]["count"] += 1
            tool_stats[name]["total_duration"] += duration
            if not success:
                tool_stats[name]["errors"] += 1

    print("\n--- Tool Execution Statistics (General) ---")
    print(f"{'Tool Name':<40} {'Count':<10} {'Total Dur (ms)':<15} {'Avg Dur (ms)':<15} {'Errors':<10}")
    print("-" * 100)
    for name, stats in sorted(tool_stats.items(), key=lambda x: x[1]['count'], reverse=True):
        avg_duration = stats["total_duration"] / stats["count"] if stats["count"] > 0 else 0
        print(f"{name:<40} {stats['count']:<10} {stats['total_duration']:<15.2f} {avg_duration:<15.2f} {stats['errors']:<10}")

def analyze_llm(logs):
    llm_stats = defaultdict(lambda: {
        "count": 0, "total_duration": 0, "total_tokens": 0, "errors": 0,
        "breakdown": defaultdict(int)
    })

    for log in logs:
        if log["event_type"] == "llm_call":
            data = log["data"]
            model = data.get("model", "unknown")
            duration = data.get("duration_ms", 0)
            success = data.get("success", True)
            tokens = data.get("prompt_tokens", 0) + data.get("completion_tokens", 0)

            # Aggregate breakdown if available
            breakdown = data.get("token_breakdown")
            if breakdown:
                for k, v in breakdown.items():
                    llm_stats[model]["breakdown"][k] += v

            llm_stats[model]["count"] += 1
            llm_stats[model]["total_duration"] += duration
            llm_stats[model]["total_tokens"] += tokens
            if not success:
               llm_stats[model]["errors"] += 1

    print("\n--- LLM Statistics ---")
    print(f"{'Model Name':<40} {'Count':<10} {'Total Dur (ms)':<15} {'Avg Dur (ms)':<15} {'Avg Tokens':<15} {'Errors':<10}")
    print("-" * 115)
    for name, stats in sorted(llm_stats.items(), key=lambda x: x[1]['count'], reverse=True):
        avg_duration = stats["total_duration"] / stats["count"] if stats["count"] > 0 else 0
        avg_tokens = stats["total_tokens"] / stats["count"] if stats["count"] > 0 else 0
        print(f"{name:<40} {stats['count']:<10} {stats['total_duration']:<15.2f} {avg_duration:<15.2f} {avg_tokens:<15.0f} {stats['errors']:<10}")
        
        # Display breakdown if available
        if stats["breakdown"] and stats["total_tokens"] > 0:
            print(f"  Token Breakdown (Avg per call):")
            for k, v in sorted(stats["breakdown"].items(), key=lambda x: x[1], reverse=True):
                 avg_k = v / stats["count"]
                 pct = (v / stats["total_tokens"]) * 100
                 print(f"    - {k:<25} {avg_k:<10.0f} ({pct:.1f}%)")
            print()

def analyze_agent(logs):
    agent_logs = [l for l in logs if l["event_type"] == "agent_execution"]
    print("\n--- Agent Execution Summary ---")
    print(f"Total Agent Runs: {len(agent_logs)}")
    if agent_logs:
        total_duration = sum(l["data"].get("duration_ms", 0) for l in agent_logs)
        avg_duration = total_duration / len(agent_logs)
        print(f"Total Run Duration: {total_duration:.2f} ms")
        print(f"Average Run Duration: {avg_duration:.2f} ms")

def analyze_sandbox(logs):
    sandbox_logs = [l for l in logs if l["event_type"] == "agent_sandbox"]
    print("\n--- Sandbox Statistics ---")
    if not sandbox_logs:
        print("No sandbox events found.")
        return

    actions = defaultdict(lambda: {"count": 0, "total_duration": 0, "errors": 0})
    for log in sandbox_logs:
        data = log["data"]
        action = data.get("action", "unknown")
        duration = data.get("duration_ms", 0)
        details = data.get("details", {})
        success = details.get("success", True)

        actions[action]["count"] += 1
        actions[action]["total_duration"] += duration
        if not success:
            actions[action]["errors"] += 1

    print(f"{'Action':<30} {'Count':<10} {'Total Dur (ms)':<15} {'Avg Dur (ms)':<15} {'Errors':<10}")
    print("-" * 90)
    for action, stats in sorted(actions.items(), key=lambda x: x[1]['count'], reverse=True):
        avg_duration = stats["total_duration"] / stats["count"] if stats["count"] > 0 else 0
        print(f"{action:<30} {stats['count']:<10} {stats['total_duration']:<15.2f} {avg_duration:<15.2f} {stats['errors']:<10}")

def analyze_context(logs):
    # Analyze tools related to context and task management
    context_tools = {"create_tasks", "update_tasks", "view_tasks", "complete"}
    
    ctx_logs = [l for l in logs if l["event_type"] == "tool_execution" and l["data"].get("tool_name") in context_tools]
    
    print("\n--- Context Management Statistics (Tasks) ---")
    if not ctx_logs:
        print("No context/task management events found.")
        return

    total_count = len(ctx_logs)
    total_duration = sum(l["data"].get("duration_ms", 0) for l in ctx_logs)
    avg_duration = total_duration / total_count if total_count > 0 else 0
    
    print(f"Total Context Operations: {total_count}")
    print(f"Total Duration: {total_duration:.2f} ms")
    print(f"Average Duration: {avg_duration:.2f} ms")
    
    # Breakdown
    tool_stats = defaultdict(lambda: {"count": 0, "duration": 0})
    for l in ctx_logs:
        name = l["data"].get("tool_name")
        tool_stats[name]["count"] += 1
        tool_stats[name]["duration"] += l["data"].get("duration_ms", 0)
        
    print("\nBreakdown by Operation:")
    print(f"{'Operation':<20} {'Count':<10} {'Total Dur (ms)':<15} {'Avg Dur (ms)':<15}")
    print("-" * 65)
    for name, stats in sorted(tool_stats.items(), key=lambda x: x[1]['count'], reverse=True):
         avg = stats["duration"] / stats["count"]
         print(f"{name:<20} {stats['count']:<10} {stats['duration']:<15.2f} {avg:<15.2f}")

def analyze_memory(logs):
    # Analyze tools related to memory management
    memory_tools = {"manage_core_memory"}
    
    mem_logs = [l for l in logs if l["event_type"] == "tool_execution" and l["data"].get("tool_name") in memory_tools]
    
    print("\n--- Memory Management Statistics ---")
    if not mem_logs:
        print("No memory management events found.")
        return

    total_count = len(mem_logs)
    total_duration = sum(l["data"].get("duration_ms", 0) for l in mem_logs)
    avg_duration = total_duration / total_count if total_count > 0 else 0
    
    print(f"Total Memory Operations: {total_count}")
    print(f"Total Duration: {total_duration:.2f} ms")
    print(f"Average Duration: {avg_duration:.2f} ms")
    
    # Breakdown
    tool_stats = defaultdict(lambda: {"count": 0, "duration": 0})
    for l in mem_logs:
        name = l["data"].get("tool_name")
        tool_stats[name]["count"] += 1
        tool_stats[name]["duration"] += l["data"].get("duration_ms", 0)
        
    print("\nBreakdown by Operation:")
    print(f"{'Operation':<20} {'Count':<10} {'Total Dur (ms)':<15} {'Avg Dur (ms)':<15}")
    print("-" * 65)
    for name, stats in sorted(tool_stats.items(), key=lambda x: x[1]['count'], reverse=True):
         avg = stats["duration"] / stats["count"]
         print(f"{name:<20} {stats['count']:<10} {stats['duration']:<15.2f} {avg:<15.2f}")


def analyze_performance(logs):
    if not logs:
        return

    # Sort logs by timestamp to ensure chronological order
    sorted_logs = sorted(logs, key=lambda x: x["timestamp"])
    
    # Calculate Total Session Duration
    start_time = datetime.fromisoformat(sorted_logs[0]["timestamp"])
    end_time = datetime.fromisoformat(sorted_logs[-1]["timestamp"])
    total_duration_delta = end_time - start_time
    total_duration_ms = total_duration_delta.total_seconds() * 1000

    # Helper to create intervals (start, end)
    def get_intervals(event_type):
        intervals = []
        for log in logs:
            if log["event_type"] == event_type:
                end = datetime.fromisoformat(log["timestamp"])
                duration = log["data"].get("duration_ms", 0)
                start = end - timedelta(milliseconds=duration)
                intervals.append((start, end))
        return intervals

    llm_intervals = get_intervals("llm_call")
    tool_intervals = get_intervals("tool_execution")
    sandbox_intervals = get_intervals("agent_sandbox")

    # Calculate Raw Durations (Sum of durations)
    total_llm_raw_ms = sum(l["data"].get("duration_ms", 0) for l in logs if l["event_type"] == "llm_call")
    total_tool_raw_ms = sum(l["data"].get("duration_ms", 0) for l in logs if l["event_type"] == "tool_execution")
    total_sandbox_raw_ms = sum(l["data"].get("duration_ms", 0) for l in logs if l["event_type"] == "agent_sandbox")

    # Calculate Overlap between LLM and Tool
    total_overlap_ms = 0
    # A simple n^2 approach for overlap is fine for log size
    # But better to use merged intervals for precise overlap if needed.
    # Here we just want the intersection sum.
    # Let's use a discretized approach or interval intersection logic.
    
    # We will use a robust interval union/intersection method
    def merge_intervals(intervals):
        if not intervals:
            return []
        intervals.sort(key=lambda x: x[0])
        merged = [intervals[0]]
        for current in intervals[1:]:
            last = merged[-1]
            if current[0] < last[1]: # Overlap
                merged[-1] = (last[0], max(last[1], current[1]))
            else:
                merged.append(current)
        return merged

    def calculate_duration(intervals):
        merged = merge_intervals(intervals)
        total = 0
        for start, end in merged:
            total += (end - start).total_seconds() * 1000
        return total

    # Union of all active intervals (LLM U Tool U Sandbox)
    all_intervals = llm_intervals + tool_intervals + sandbox_intervals
    total_active_ms = calculate_duration(all_intervals)
    
    # System Overhead = Total Session - Active Time
    # Note: If Active Time > Total Session (due to clock skew or start/end definition), clamp to 0?
    # Actually, start/end are defined by first/last log. 
    # It is possible an event started BEFORE the first log (if first log is end of something long).
    # But here first log is likely agent_execution start or similar.
    # Let's assume start_time is reliable enough.
    
    system_overhead_ms = max(0, total_duration_ms - total_active_ms)

    # Calculate LLM & Tool Overlap specifically
    # Intersection of Union(LLM) and Union(Tool)
    merged_llm = merge_intervals(llm_intervals)
    merged_tool = merge_intervals(tool_intervals)
    
    overlap_ms = 0
    for l_start, l_end in merged_llm:
        for t_start, t_end in merged_tool:
            latest_start = max(l_start, t_start)
            earliest_end = min(l_end, t_end)
            if latest_start < earliest_end:
                overlap_ms += (earliest_end - latest_start).total_seconds() * 1000

    print("\n--- End-to-End Performance Statistics ---")
    print(f"Total Session Duration: {total_duration_ms/1000:.2f} s")
    
    print("\nComponent Durations (Independent & Raw):")
    print(f"- LLM Call Duration: {total_llm_raw_ms/1000:.2f} s")
    print(f"- Tool Execution Duration: {total_tool_raw_ms/1000:.2f} s")
    print(f"- Sandbox Execution Duration: {total_sandbox_raw_ms/1000:.2f} s")
    
    print("\nAnalysis:")
    print(f"- Sum of LLM & Tool: {(total_llm_raw_ms + total_tool_raw_ms)/1000:.2f} s")
    print(f"- Calculated Overlap (LLM & Tool): {overlap_ms/1000:.2f} s")
    if overlap_ms > 0:
        print(f"  (Note: {overlap_ms/1000:.2f}s of Tool Execution occurred during LLM Streaming)")

    print("\nSystem Breakdown:")
    print(f"- Effective Active Time (Union of all events): {total_active_ms/1000:.2f} s")
    print(f"- Other System Overhead: {system_overhead_ms/1000:.2f} s")
    print(f"  (Time not accounted for by LLM, Tool, or Sandbox events)")
    
    print(f"\nStart Time: {sorted_logs[0]['timestamp']}")
    print(f"End Time: {sorted_logs[-1]['timestamp']}")

def main():
    parser = argparse.ArgumentParser(description="View local observability metrics")
    parser.add_argument("--file", help="Path to jsonl log file")
    parser.add_argument("--trace-id", help="Filter by specific trace ID")
    args = parser.parse_args()

    global LOG_FILE
    
    if args.file:
        LOG_FILE = args.file
    else:
        # Find latest log file
        logs_dir = os.path.join(os.getcwd(), "logs")
        if os.path.exists(logs_dir):
            # Match metrics_logs_*.jsonl and the original metrics_logs.jsonl
            log_files = [f for f in os.listdir(logs_dir) if (f.startswith("metrics_logs_") or f == "metrics_logs.jsonl") and f.endswith(".jsonl")]
            if log_files:
                # Sort by name (which works for timestamps) to get the latest
                latest_log = sorted(log_files)[-1]
                LOG_FILE = os.path.join(logs_dir, latest_log)
                print(f"Using latest log file: {LOG_FILE}")
            else:
                 LOG_FILE = "metrics_logs.jsonl"
        else:
             LOG_FILE = "metrics_logs.jsonl"

    logs = load_logs()

    if not logs:
        print("No logs found.")
        return

    # Group logs by trace_id
    traces = defaultdict(list)
    for log in logs:
        # Default to 'unknown' if trace_id is missing (for backward compatibility)
        trace_id = log.get("trace_id")
        if trace_id is None:
            trace_id = "unknown"
        traces[trace_id].append(log)

    # If trace_id is specified, show only that trace
    if args.trace_id:
        if args.trace_id not in traces:
            print(f"Trace ID '{args.trace_id}' not found.")
            return
        
        print(f"\n{'='*80}")
        print(f"ANALYSIS FOR TRACE: {args.trace_id}")
        print(f"{'='*80}")
        trace_logs = traces[args.trace_id]
        analyze_performance(trace_logs)
        analyze_agent(trace_logs)
        analyze_context(trace_logs)
        analyze_memory(trace_logs)
        analyze_sandbox(trace_logs)
        analyze_llm(trace_logs)
        analyze_tools(trace_logs)
        return

    # Otherwise, show summary of all traces and then details for each
    print(f"\nFound {len(traces)} traces:")
    print(f"{'Trace ID':<40} {'Events':<10} {'Start Time':<30} {'Duration (s)':<15}")
    print("-" * 100)
    
    sorted_trace_ids = []
    
    for trace_id, trace_logs in traces.items():
        sorted_logs = sorted(trace_logs, key=lambda x: x["timestamp"])
        start_time = datetime.fromisoformat(sorted_logs[0]["timestamp"])
        end_time = datetime.fromisoformat(sorted_logs[-1]["timestamp"])
        duration = (end_time - start_time).total_seconds()
        
        print(f"{str(trace_id):<40} {len(trace_logs):<10} {sorted_logs[0]['timestamp']:<30} {duration:<15.2f}")
        sorted_trace_ids.append((trace_id, start_time))

    # Sort traces by start time for detailed display
    sorted_trace_ids.sort(key=lambda x: x[1])

    for trace_id, _ in sorted_trace_ids:
        print(f"\n\n{'#'*100}")
        print(f"TRACE: {trace_id}")
        print(f"{'#'*100}")
        
        trace_logs = traces[trace_id]
        analyze_performance(trace_logs)
        analyze_agent(trace_logs)
        analyze_context(trace_logs)
        analyze_memory(trace_logs)
        analyze_sandbox(trace_logs)
        analyze_llm(trace_logs)
        analyze_tools(trace_logs)

if __name__ == "__main__":
    main()
