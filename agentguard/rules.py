"""Built-in guardrail rules."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuleResult:
    """Result of a single rule check."""
    passed: bool
    reason: str = ""
    filtered_text: str | None = None


@dataclass
class Rule:
    """Base rule definition."""
    name: str
    applies_to: str  # "input", "output", "tool"
    _check_fn: Any = None
    _check_tool_fn: Any = None

    def check(self, text: str) -> RuleResult:
        if self._check_fn:
            return self._check_fn(text)
        return RuleResult(passed=True)

    def check_tool(self, tool_name: str, params: dict) -> RuleResult:
        if self._check_tool_fn:
            return self._check_tool_fn(tool_name, params)
        return RuleResult(passed=True)


class Rules:
    """Factory for built-in guardrail rules."""

    # ── Input Rules ──────────────────────────────────────────

    @staticmethod
    def no_prompt_injection() -> Rule:
        """Detect prompt injection attempts."""
        PATTERNS = [
            r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|rules)",
            r"system\s*prompt",
            r"you\s+are\s+now\s+",
            r"disregard\s+(your|all|the)\s+",
            r"forget\s+(everything|your|all)",
            r"override\s+(your|the)\s+",
            r"new\s+instructions?\s*:",
        ]

        def check(text: str) -> RuleResult:
            for pattern in PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    return RuleResult(
                        passed=False,
                        reason=f"Detected instruction override attempt",
                    )
            return RuleResult(passed=True)

        return Rule(name="no_prompt_injection", applies_to="input", _check_fn=check)

    @staticmethod
    def no_jailbreak() -> Rule:
        """Block common jailbreak patterns."""
        PATTERNS = [
            r"\bDAN\b",
            r"do anything now",
            r"pretend you (are|have no)",
            r"act as if you (have no|don't have)",
            r"in developer mode",
            r"ignore.*safety",
        ]

        def check(text: str) -> RuleResult:
            for pattern in PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    return RuleResult(passed=False, reason="Jailbreak attempt detected")
            return RuleResult(passed=True)

        return Rule(name="no_jailbreak", applies_to="input", _check_fn=check)

    @staticmethod
    def max_input_tokens(limit: int = 2000) -> Rule:
        """Reject oversized inputs."""
        def check(text: str) -> RuleResult:
            est_tokens = len(text) // 4
            if est_tokens > limit:
                return RuleResult(passed=False, reason=f"Input too long: ~{est_tokens} tokens (limit: {limit})")
            return RuleResult(passed=True)

        return Rule(name="max_input_tokens", applies_to="input", _check_fn=check)

    # ── Output Rules ─────────────────────────────────────────

    @staticmethod
    def no_pii_leakage() -> Rule:
        """Redact PII from outputs (emails, SSNs, phone numbers)."""
        PII_PATTERNS = [
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),
            (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),
            (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE_REDACTED]"),
        ]

        def check(text: str) -> RuleResult:
            filtered = text
            found = False
            for pattern, replacement in PII_PATTERNS:
                if re.search(pattern, filtered):
                    filtered = re.sub(pattern, replacement, filtered)
                    found = True
            if found:
                return RuleResult(passed=False, reason="PII detected", filtered_text=filtered)
            return RuleResult(passed=True)

        return Rule(name="no_pii_leakage", applies_to="output", _check_fn=check)

    @staticmethod
    def no_internal_urls() -> Rule:
        """Strip internal hostnames and paths."""
        INTERNAL_PATTERNS = [
            r"https?://[a-z0-9.-]+\.(corp|internal|local|intranet)\b[^\s]*",
            r"https?://10\.\d+\.\d+\.\d+[^\s]*",
            r"https?://192\.168\.\d+\.\d+[^\s]*",
            r"/etc/passwd|/var/log|C:\\Windows",
        ]

        def check(text: str) -> RuleResult:
            filtered = text
            found = False
            for pattern in INTERNAL_PATTERNS:
                if re.search(pattern, filtered, re.IGNORECASE):
                    filtered = re.sub(pattern, "[INTERNAL_URL_REDACTED]", filtered, flags=re.IGNORECASE)
                    found = True
            if found:
                return RuleResult(passed=False, reason="Internal URL detected", filtered_text=filtered)
            return RuleResult(passed=True)

        return Rule(name="no_internal_urls", applies_to="output", _check_fn=check)

    @staticmethod
    def no_credentials() -> Rule:
        """Detect and redact API keys, passwords, tokens."""
        CRED_PATTERNS = [
            (r"(api[_-]?key|apikey)\s*[:=]\s*\S+", "[API_KEY_REDACTED]"),
            (r"(password|passwd|pwd)\s*[:=]\s*\S+", "[PASSWORD_REDACTED]"),
            (r"(bearer|token)\s+[A-Za-z0-9._-]{20,}", "[TOKEN_REDACTED]"),
            (r"sk-[A-Za-z0-9]{20,}", "[OPENAI_KEY_REDACTED]"),
        ]

        def check(text: str) -> RuleResult:
            filtered = text
            found = False
            for pattern, replacement in CRED_PATTERNS:
                if re.search(pattern, filtered, re.IGNORECASE):
                    filtered = re.sub(pattern, replacement, filtered, flags=re.IGNORECASE)
                    found = True
            if found:
                return RuleResult(passed=False, reason="Credentials detected", filtered_text=filtered)
            return RuleResult(passed=True)

        return Rule(name="no_credentials", applies_to="output", _check_fn=check)

    @staticmethod
    def max_output_tokens(limit: int = 2000) -> Rule:
        """Cap output length."""
        def check(text: str) -> RuleResult:
            est_tokens = len(text) // 4
            if est_tokens > limit:
                # Truncate rather than block
                char_limit = limit * 4
                filtered = text[:char_limit] + "\n\n[Output truncated for safety]"
                return RuleResult(passed=False, reason="Output exceeds limit", filtered_text=filtered)
            return RuleResult(passed=True)

        return Rule(name="max_output_tokens", applies_to="output", _check_fn=check)

    # ── Tool Rules ───────────────────────────────────────────

    @staticmethod
    def tool_allowlist(allowed: list[str]) -> Rule:
        """Only allow specific tools to execute."""
        def check_tool(tool_name: str, params: dict) -> RuleResult:
            if tool_name not in allowed:
                return RuleResult(passed=False, reason=f"'{tool_name}' not in allowed tools")
            return RuleResult(passed=True)

        return Rule(name="tool_allowlist", applies_to="tool", _check_tool_fn=check_tool)

    @staticmethod
    def tool_blocklist(blocked: list[str]) -> Rule:
        """Block specific dangerous tools."""
        def check_tool(tool_name: str, params: dict) -> RuleResult:
            if tool_name in blocked:
                return RuleResult(passed=False, reason=f"'{tool_name}' is blocked")
            return RuleResult(passed=True)

        return Rule(name="tool_blocklist", applies_to="tool", _check_tool_fn=check_tool)
