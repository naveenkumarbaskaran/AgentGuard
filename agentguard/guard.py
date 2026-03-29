"""Core Guard class — validates inputs, outputs, and tool calls."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agentguard.rules import Rule
from agentguard.results import InputResult, OutputResult, ToolResult


@dataclass
class Guard:
    """
    Main guardrail engine.

    Applies rules to validate agent inputs, outputs, and tool calls.
    Rules are composable — add as many as needed.
    """

    rules: list[Rule] = field(default_factory=list)

    def check_input(self, text: str) -> InputResult:
        """Validate user input against input rules."""
        for rule in self.rules:
            if rule.applies_to != "input":
                continue
            result = rule.check(text)
            if not result.passed:
                return InputResult(
                    passed=False,
                    blocked_by=rule.name,
                    reason=result.reason,
                )
        return InputResult(passed=True)

    def check_output(self, text: str) -> OutputResult:
        """Validate/filter agent output against output rules."""
        filtered_text = text
        applied_filters: list[str] = []

        for rule in self.rules:
            if rule.applies_to != "output":
                continue
            result = rule.check(filtered_text)
            if not result.passed:
                if result.filtered_text:
                    filtered_text = result.filtered_text
                    applied_filters.append(rule.name)
                else:
                    return OutputResult(
                        passed=False,
                        blocked_by=rule.name,
                        reason=result.reason,
                    )

        if applied_filters:
            return OutputResult(
                passed=True,
                filtered=True,
                text=filtered_text,
                filters_applied=applied_filters,
            )
        return OutputResult(passed=True, text=text)

    def check_tool(self, tool_name: str, params: dict[str, Any] | None = None) -> ToolResult:
        """Validate a tool call against tool rules."""
        for rule in self.rules:
            if rule.applies_to != "tool":
                continue
            result = rule.check_tool(tool_name, params or {})
            if not result.passed:
                return ToolResult(
                    passed=False,
                    blocked_by=rule.name,
                    reason=result.reason,
                )
        return ToolResult(passed=True, tool_name=tool_name)
