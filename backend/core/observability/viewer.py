import json
import os
from collections import defaultdict
from datetime import datetime
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
    print(f"{'Tool Name':<40} {'Count':<10} {'Avg Duration (ms)':<20} {'Errors':<10}")
    print("-" * 80)
    for name, stats in sorted(tool_stats.items(), key=lambda x: x[1]['count'], reverse=True):
        avg_duration = stats["total_duration"] / stats["count"] if stats["count"] > 0 else 0
        print(f"{name:<40} {stats['count']:<10} {avg_duration:<20.2f} {stats['errors']:<10}")

def analyze_llm(logs):
    llm_stats = defaultdict(lambda: {"count": 0, "total_duration": 0, "total_tokens": 0, "errors": 0})

    for log in logs:
        if log["event_type"] == "llm_call":
            data = log["data"]
            model = data.get("model", "unknown")
            duration = data.get("duration_ms", 0)
            success = data.get("success", True)
            tokens = data.get("prompt_tokens", 0) + data.get("completion_tokens", 0)

            llm_stats[model]["count"] += 1
            llm_stats[model]["total_duration"] += duration
            llm_stats[model]["total_tokens"] += tokens
            if not success:
               llm_stats[model]["errors"] += 1

    print("\n--- LLM Statistics ---")
    print(f"{'Model Name':<40} {'Count':<10} {'Avg Duration (ms)':<20} {'Avg Tokens':<15} {'Errors':<10}")
    print("-" * 100)
    for name, stats in sorted(llm_stats.items(), key=lambda x: x[1]['count'], reverse=True):
        avg_duration = stats["total_duration"] / stats["count"] if stats["count"] > 0 else 0
        avg_tokens = stats["total_tokens"] / stats["count"] if stats["count"] > 0 else 0
        print(f"{name:<40} {stats['count']:<10} {avg_duration:<20.2f} {avg_tokens:<15.0f} {stats['errors']:<10}")

def analyze_agent(logs):
    agent_logs = [l for l in logs if l["event_type"] == "agent_execution"]
    print("\n--- Agent Execution Summary ---")
    print(f"Total Agent Runs: {len(agent_logs)}")
    if agent_logs:
        avg_duration = sum(l["data"].get("duration_ms", 0) for l in agent_logs) / len(agent_logs)
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

    print(f"{'Action':<30} {'Count':<10} {'Avg Duration (ms)':<20} {'Errors':<10}")
    print("-" * 75)
    for action, stats in sorted(actions.items(), key=lambda x: x[1]['count'], reverse=True):
        avg_duration = stats["total_duration"] / stats["count"] if stats["count"] > 0 else 0
        print(f"{action:<30} {stats['count']:<10} {avg_duration:<20.2f} {stats['errors']:<10}")

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
    print(f"Average Duration: {avg_duration:.2f} ms")
    
    # Breakdown
    tool_stats = defaultdict(lambda: {"count": 0, "duration": 0})
    for l in ctx_logs:
        name = l["data"].get("tool_name")
        tool_stats[name]["count"] += 1
        tool_stats[name]["duration"] += l["data"].get("duration_ms", 0)
        
    print("\nBreakdown by Operation:")
    print(f"{'Operation':<20} {'Count':<10} {'Avg Duration (ms)':<20}")
    print("-" * 55)
    for name, stats in sorted(tool_stats.items(), key=lambda x: x[1]['count'], reverse=True):
         avg = stats["duration"] / stats["count"]
         print(f"{name:<20} {stats['count']:<10} {avg:<20.2f}")

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
    print(f"Average Duration: {avg_duration:.2f} ms")
    
    # Breakdown
    tool_stats = defaultdict(lambda: {"count": 0, "duration": 0})
    for l in mem_logs:
        name = l["data"].get("tool_name")
        tool_stats[name]["count"] += 1
        tool_stats[name]["duration"] += l["data"].get("duration_ms", 0)
        
    print("\nBreakdown by Operation:")
    print(f"{'Operation':<20} {'Count':<10} {'Avg Duration (ms)':<20}")
    print("-" * 55)
    for name, stats in sorted(tool_stats.items(), key=lambda x: x[1]['count'], reverse=True):
         avg = stats["duration"] / stats["count"]
         print(f"{name:<20} {stats['count']:<10} {avg:<20.2f}")


def main():
    parser = argparse.ArgumentParser(description="View local observability metrics")
    parser.add_argument("--file", default="metrics_logs.jsonl", help="Path to jsonl log file")
    args = parser.parse_args()

    global LOG_FILE
    LOG_FILE = args.file

    logs = load_logs()

    if not logs:
        print("No logs found.")
        return

    analyze_agent(logs)
    analyze_context(logs)
    analyze_memory(logs)
    analyze_sandbox(logs)
    analyze_llm(logs)
    analyze_tools(logs)

if __name__ == "__main__":
    main()
