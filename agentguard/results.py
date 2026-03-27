"""Result types for guard checks."""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class InputResult:
    passed: bool
    blocked_by: str = ""
    reason: str = ""


@dataclass
class OutputResult:
    passed: bool
    filtered: bool = False
    text: str = ""
    blocked_by: str = ""
    reason: str = ""
    filters_applied: list[str] = field(default_factory=list)


@dataclass
class ToolResult:
    passed: bool
    tool_name: str = ""
    blocked_by: str = ""
    reason: str = ""
