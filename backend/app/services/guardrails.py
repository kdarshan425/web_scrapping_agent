"""Guardrails: rule-based checks on the way IN and on the way OUT. Zero token cost.

INPUT  : empty/too long question, prompt-injection attempts, injected lines hidden in web pages.
OUTPUT : system-prompt leak, unsafe content, PII / secrets redaction, empty answer, length cap.
"""
import re
from dataclasses import dataclass, field

from app.services.prompts import PROMPT_MARKER

# ---------- patterns ----------
_INJECTION = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"ignore (all |any |the )?(previous|prior|above|earlier) (instructions|prompts?|rules)",
        r"disregard (all |any |the )?(previous|prior|above|earlier)",
        r"(reveal|show|print|repeat) (me )?(your|the) (system )?(prompt|instructions|rules)",
        r"you are now (dan|in developer mode|unrestricted)",
        r"act as (an? )?(unrestricted|jailbroken|evil)",
        r"forget (everything|all) (you|above)",
    )
]
_UNSAFE_OUTPUT = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"how to (make|build|create) (a )?(bomb|explosive|bioweapon|nerve agent)",
        r"step[- ]by[- ]step.{0,40}(synthesi[sz]e|manufacture).{0,40}(meth|explosive|nerve agent)",
    )
]
_PII = {  # order matters: most specific first
    "api_key": re.compile(r"\b(?:sk|gsk|pk|rk)[-_][A-Za-z0-9_\-]{16,}\b|\bAKIA[0-9A-Z]{16}\b"),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "aadhaar": re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b"),
    "card": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "phone": re.compile(r"(?<!\d)(?:\+?\d{1,3}[\s-]?)?\d{10}(?!\d)"),
}


def _luhn_ok(number: str) -> bool:
    """Credit-card checksum, so random long numbers are not redacted as cards."""
    digits = [int(c) for c in number if c.isdigit()][::-1]
    total = sum(d if i % 2 == 0 else (d * 2 - 9 if d * 2 > 9 else d * 2) for i, d in enumerate(digits))
    return len(digits) >= 13 and total % 10 == 0


@dataclass
class InputCheck:
    ok: bool
    message: str = ""
    reason: str = ""


@dataclass
class OutputCheck:
    text: str
    ok: bool = True
    escalate: bool = False  # True = retry with a stronger model may help
    flags: list[str] = field(default_factory=list)


class InputGuard:
    def __init__(self, max_question_chars: int) -> None:
        self.max_question_chars = max_question_chars

    def check(self, question: str) -> InputCheck:
        if not question.strip():
            return InputCheck(False, "Please type a question.", "empty")
        if len(question) > self.max_question_chars:
            return InputCheck(False, f"Question too long (max {self.max_question_chars} characters).", "too_long")
        if any(p.search(question) for p in _INJECTION):
            return InputCheck(False, "I can't process that request.", "prompt_injection")
        return InputCheck(True)

    def sanitize_page(self, page_text: str) -> tuple[str, list[str]]:
        """Indirect prompt injection defence: drop page lines that try to command the AI."""
        flags, clean = [], []
        for line in page_text.splitlines():
            if any(p.search(line) for p in _INJECTION):
                clean.append("[removed: suspicious instruction]")
                if "page_injection_removed" not in flags:
                    flags.append("page_injection_removed")
            else:
                clean.append(line)
        return "\n".join(clean), flags


class OutputGuard:
    def __init__(self, max_answer_chars: int, redact_pii: bool) -> None:
        self.max_answer_chars = max_answer_chars
        self.redact_pii = redact_pii

    def check(self, answer: str) -> OutputCheck:
        text = answer.strip()
        if len(text) < 2:
            return OutputCheck("", ok=False, escalate=True, flags=["empty_answer"])
        if PROMPT_MARKER in text:
            return OutputCheck("", ok=False, flags=["system_prompt_leak"])
        if any(p.search(text) for p in _UNSAFE_OUTPUT):
            return OutputCheck("", ok=False, flags=["unsafe_content"])

        flags: list[str] = []
        if self.redact_pii:
            text, flags = self._redact(text)
        if len(text) > self.max_answer_chars:
            text = text[: self.max_answer_chars].rstrip() + " …"
            flags.append("truncated")
        return OutputCheck(text, flags=flags)

    @staticmethod
    def _redact(text: str) -> tuple[str, list[str]]:
        flags: list[str] = []
        for name, pattern in _PII.items():
            def repl(m: re.Match, name=name) -> str:
                if name == "card" and not _luhn_ok(m.group()):
                    return m.group()  # not a real card number
                if f"pii_{name}_redacted" not in flags:
                    flags.append(f"pii_{name}_redacted")
                return f"[{name.upper()} REDACTED]"

            text = pattern.sub(repl, text)
        return text, flags
