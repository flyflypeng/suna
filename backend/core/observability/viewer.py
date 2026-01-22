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
    tool_stats = defaultdict(lambda: {"count": 0, "total_duration": 0, "errors": 0})

    for log in logs:
        if log["event_type"] == "tool_execution":
            data = log["data"]
            name = data.get("tool_name", "unknown")
            duration = data.get("duration_ms", 0)
            success = data.get("success", True)

            tool_stats[name]["count"] += 1
            tool_stats[name]["total_duration"] += duration
            if not success:
                tool_stats[name]["errors"] += 1

    print("\n--- Tool Execution Statistics ---")
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
    analyze_llm(logs)
    analyze_tools(logs)

if __name__ == "__main__":
    main()
