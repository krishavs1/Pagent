"""
Structured logging utilities for the agent.

Planned responsibilities:
- Emit JSONL logs for easy replay in backtests
- Provide contextual fields (run_id, market_id, signal_id) for tracing
- Support both console and file sinks

This scaffold provides a minimal interface only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(slots=True)
class AgentLogger:
    """Structured logger intended for JSON-line event emission."""

    name: str
    sink_path: Optional[str] = None

    def info(self, event: str, fields: Optional[Dict[str, Any]] = None) -> None:
        """Log an informational event."""
        pass

    def warning(self, event: str, fields: Optional[Dict[str, Any]] = None) -> None:
        """Log a warning event."""
        pass

    def error(self, event: str, fields: Optional[Dict[str, Any]] = None) -> None:
        """Log an error event."""
        pass

