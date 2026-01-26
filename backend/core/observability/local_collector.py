import json
import time
import os
import uuid
import contextvars
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from core.utils.logger import logger

# Context variable to store trace_id for current execution context
_trace_context = contextvars.ContextVar("trace_id", default=None)

class LocalMetricsCollector:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LocalMetricsCollector, cls).__new__(cls, *args, **kwargs)
            logs_dir = os.path.join(os.getcwd(), "logs")
            os.makedirs(logs_dir, exist_ok=True)
            cls._instance.log_file = os.path.join(logs_dir, "metrics_logs.jsonl")
        return cls._instance

    def set_context(self, trace_id: str):
        """Set the trace_id for the current context."""
        return _trace_context.set(trace_id)

    def get_context(self) -> Optional[str]:
        """Get the trace_id for the current context."""
        return _trace_context.get()

    def clear_context(self, token):
        """Reset the context to the previous state."""
        _trace_context.reset(token)

    def log_event(self, event_type: str, data: Dict[str, Any]):
        """
        Log an event to the local metrics file.

        Args:
            event_type (str): The type of event (e.g., 'llm_call', 'tool_execution').
            data (Dict[str, Any]): The data to log.
        """
        trace_id = self.get_context()
        
        # If data already has trace_id, use it as the source of truth
        if "trace_id" in data:
            trace_id = data["trace_id"]
        
        # If data already has trace_id, use it, otherwise use context trace_id
        if trace_id and "trace_id" not in data:
             # We can add it to data or keep it at top level. 
             # Keeping it at top level is cleaner for filtering.
             pass

        event = {
            "event_id": str(uuid.uuid4()),
            "trace_id": trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "data": data
        }

        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Failed to write local metrics: {e}")

    def log_llm_call(self, model: str, prompt_tokens: int, completion_tokens: int, duration_ms: float, thread_id: str, success: bool = True, token_breakdown: Optional[Dict[str, int]] = None):
        self.log_event("llm_call", {
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "duration_ms": duration_ms,
            "thread_id": thread_id,
            "success": success,
            "token_breakdown": token_breakdown
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

    def log_memory_event(self, action: str, duration_ms: float, details: Dict[str, Any]):
        """
        Log memory related events (retrieval, storage).
        """
        self.log_event("agent_memory", {
            "action": action,
            "duration_ms": duration_ms,
            "details": details
        })

    def log_sandbox_event(self, action: str, duration_ms: float, details: Dict[str, Any]):
        """
        Log sandbox related events (create, execute, delete).
        """
        self.log_event("agent_sandbox", {
            "action": action,
            "duration_ms": duration_ms,
            "details": details
        })

    def log_context_event(self, action: str, duration_ms: float, details: Dict[str, Any]):
        """
        Log context processing related events (compression, pruning).
        """
        self.log_event("agent_context", {
            "action": action,
            "duration_ms": duration_ms,
            "details": details
        })

local_collector = LocalMetricsCollector()
