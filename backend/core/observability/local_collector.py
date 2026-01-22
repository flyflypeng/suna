import json
import time
import os
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from core.utils.logger import logger

class LocalMetricsCollector:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LocalMetricsCollector, cls).__new__(cls, *args, **kwargs)
            cls._instance.log_file = os.path.join(os.getcwd(), "metrics_logs.jsonl")
        return cls._instance

    def log_event(self, event_type: str, data: Dict[str, Any]):
        """
        Log an event to the local metrics file.

        Args:
            event_type (str): The type of event (e.g., 'llm_call', 'tool_execution').
            data (Dict[str, Any]): The data to log.
        """
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "data": data
        }

        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Failed to write local metrics: {e}")

    def log_llm_call(self, model: str, prompt_tokens: int, completion_tokens: int, duration_ms: float, thread_id: str, success: bool = True):
        self.log_event("llm_call", {
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "duration_ms": duration_ms,
            "thread_id": thread_id,
            "success": success
        })

    def log_tool_execution(self, tool_name: str, method_name: str, duration_ms: float, thread_id: str, success: bool = True):
        self.log_event("tool_execution", {
            "tool_name": tool_name,
            "method_name": method_name,
            "duration_ms": duration_ms,
            "thread_id": thread_id,
            "success": success
        })

    def log_agent_execution(self, thread_id: str, trace_id: str, duration_ms: float, steps: int):
         self.log_event("agent_execution", {
            "thread_id": thread_id,
            "trace_id": trace_id,
            "duration_ms": duration_ms,
            "steps": steps
        })

local_collector = LocalMetricsCollector()
