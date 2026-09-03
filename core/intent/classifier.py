"""
Intent classification for NALA chat vs task routing.

Tier 1: fast heuristic patterns (default path for most messages).
Tier 2: lightweight keyword / structure scorer when Tier 1 is ambiguous.
Tier 3: optional tiny Ollama one-token disambiguation (best-effort, non-blocking budget).

On failure or low confidence, defaults to CHAT (safer UX — avoids false full pipeline).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional, Tuple

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    CHAT = "chat"
    TASK = "task"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class IntentResult:
    intent: Literal["chat", "task"]
    raw: Intent
    confidence: float
    tier: int
    reason: str


# --- Tier 1: compiled heuristics -------------------------------------------------

_CHAT_EXACT = re.compile(
    r"^\s*("
    r"hi|hello|hey|yo|sup|greetings|"
    r"good\s+(morning|afternoon|evening|night)|"
    r"how\s+are\s+you|how'?s\s+it\s+going|what'?s\s+up|how\s+do\s+you\s+do|"
    r"thank\s+you|thanks|thx|appreciate\s+it|"
    r"bye|goodbye|see\s+you|later|peace|"
    r"hola|bonjour|namaste|"
    r"ok|okay|k|cool|nice|great|awesome|"
    r"who\s+are\s+you|what\s+are\s+you|what'?s\s+your\s+name|"
    r"which\s+model(\s+are\s+you\s+using)?|what\s+model(\s+are\s+you\s+using)?|"
    r"are\s+you\s+(there|ok|ready)|"
    r"help(\s+me)?\??"
    r")\s*[.!]?\s*$",
    re.IGNORECASE,
)

_CHAT_QUESTION = re.compile(
    r"^\s*("
    r"what\s+(is|are|was|were|do|does|did|can|could|should|would)\b|"
    r"who\s+(is|are|was|were)\b|"
    r"when\s+(is|are|was|were|do|does|did)\b|"
    r"where\s+(is|are|was|were|do|does|did)\b|"
    r"why\s+(is|are|was|were|do|does|did|can|should)\b|"
    r"how\s+(do|does|did|can|could|should|would|is|are)\b|"
    r"can\s+you\s+explain|could\s+you\s+explain|please\s+explain|"
    r"does\s+this\s+look\s+right|is\s+this\s+(correct|right|ok|okay)"
    r").*",
    re.IGNORECASE,
)

_TASK_IMPERATIVE = re.compile(
    r"\b("
    r"create|make|build|write|code|develop|design|fix|debug|test|run|execute|"
    r"install|configure|deploy|generate|produce|construct|implement|optimize|"
    r"refactor|delete|remove|rename|move|copy|save|open|edit|update|add|"
    r"compile|start|stop|kill|download|upload|clone|commit|push|pull|"
    r"scaffold|bootstrap|setup|set\s+up"
    r")\b.+\b",
    re.IGNORECASE,
)

_TASK_PATH_OR_FILE = re.compile(
    r"("
    r"[A-Za-z]:\\|"  # Windows path
    r"/(?:home|Users|var|tmp|opt)/|"
    r"\b(file|directory|folder|path)\b|"
    r"\.(py|js|ts|tsx|jsx|html|css|json|yaml|yml|txt|md|log|rs|go|java)\b"
    r")",
    re.IGNORECASE,
)

_TASK_CLI = re.compile(
    r"\b(sudo|apt|pip|npm|yarn|pnpm|docker|kubectl|git|ssh|scp|rsync|wget|curl|"
    r"pytest|cargo|go\s+mod|mvn|gradle)\b",
    re.IGNORECASE,
)

_TECH_KEYWORDS = re.compile(
    r"\b("
    r"algorithm|function|class|method|variable|loop|recursion|async|await|"
    r"promise|callback|api|endpoint|database|sql|query|library|framework|"
    r"deploy|container|microservice|kubernetes|docker|sandbox|checkpoint"
    r")\b",
    re.IGNORECASE,
)

_DOMAIN_KEYWORDS = re.compile(
    r"\b("
    r"python|javascript|typescript|java|cpp|c\+\+|rust|golang|go|html|css|"
    r"react|vue|angular|node|django|flask|spring|tensorflow|pytorch|"
    r"aws|azure|gcp"
    r")\b",
    re.IGNORECASE,
)

# Canned ultra-common chat replies (last-resort / instant path)
CANNED_CHAT: dict[str, str] = {
    "hi": "Hello! How can I help you today?",
    "hello": "Hello! How can I help you today?",
    "hey": "Hey! What would you like to work on?",
    "thanks": "You're welcome!",
    "thank you": "You're welcome!",
    "bye": "Goodbye! Come back anytime.",
    "goodbye": "Goodbye! Come back anytime.",
    # Identity — always answer correctly without hitting the model
    "who are you": "I am NALA (Nexus Autonomous Long-Running Agent), an advanced AI coding assistant built by Nexus LAB AI, founded by Sourav Ray. How can I help you today?",
    "what are you": "I am NALA (Nexus Autonomous Long-Running Agent), an advanced AI coding assistant built by Nexus LAB AI. I can help with code, autonomous task execution, and more!",
    "who made you": "I was built by Nexus LAB AI, founded by Sourav Ray.",
    "who created you": "I was created by Nexus LAB AI, founded by Sourav Ray.",
    "are you chatgpt": "No, I am NALA (Nexus Autonomous Long-Running Agent) by Nexus LAB AI, not ChatGPT.",
    "are you gpt": "No, I am NALA by Nexus LAB AI.",
    "what is your name": "My name is NALA — Nexus Autonomous Long-Running Agent, built by Nexus LAB AI.",
    "what's your name": "My name is NALA — Nexus Autonomous Long-Running Agent, built by Nexus LAB AI.",
}


def canned_chat_reply(prompt: str) -> Optional[str]:
    key = re.sub(r"[.!?]+$", "", prompt.strip().lower())
    return CANNED_CHAT.get(key)


def _tier1(prompt: str) -> Optional[Tuple[Intent, float, str]]:
    text = prompt.strip()
    if not text:
        return Intent.CHAT, 1.0, "empty_prompt"

    if _CHAT_EXACT.match(text):
        return Intent.CHAT, 0.98, "exact_chat_pattern"

    # Strong task signals
    task_hits = 0
    reasons = []
    if _TASK_IMPERATIVE.search(text):
        task_hits += 1
        reasons.append("imperative_verb")
    if _TASK_PATH_OR_FILE.search(text):
        task_hits += 1
        reasons.append("path_or_file")
    if _TASK_CLI.search(text):
        task_hits += 1
        reasons.append("cli_tool")

    if task_hits >= 2:
        return Intent.TASK, 0.95, "+".join(reasons)
    if task_hits == 1 and len(text) > 24:
        # Single strong task cue + non-trivial length
        if _TASK_IMPERATIVE.search(text) or _TASK_CLI.search(text):
            return Intent.TASK, 0.85, reasons[0] if reasons else "task_signal"

    # Question-framed messages without task verbs → chat
    if _CHAT_QUESTION.match(text) and task_hits == 0:
        return Intent.CHAT, 0.8, "question_framing"

    # Short soft chat
    if len(text) <= 40 and task_hits == 0 and not _TECH_KEYWORDS.search(text):
        if text.endswith("?") or len(text.split()) <= 6:
            return Intent.CHAT, 0.72, "short_conversational"

    return None


def _tier2(prompt: str) -> Tuple[Intent, float, str]:
    """Lightweight structural scorer → CHAT / TASK / AMBIGUOUS."""
    text = prompt.strip()
    words = text.split()
    score_task = 0.0
    score_chat = 0.0

    if _TASK_IMPERATIVE.search(text):
        score_task += 0.45
    if _TASK_PATH_OR_FILE.search(text):
        score_task += 0.25
    if _TASK_CLI.search(text):
        score_task += 0.3
    if _TECH_KEYWORDS.search(text):
        score_task += 0.1
    if _DOMAIN_KEYWORDS.search(text):
        score_task += 0.08

    if _CHAT_QUESTION.match(text):
        score_chat += 0.35
    if text.endswith("?") and not _TASK_IMPERATIVE.search(text):
        score_chat += 0.2
    if len(words) <= 8:
        score_chat += 0.15
    if re.search(r"\b(please\s+)?(explain|describe|tell\s+me|what\s+about)\b", text, re.I):
        score_chat += 0.25

    # Mixed: greeting + task → task wins
    if re.match(r"^\s*(hi|hello|hey)\b", text, re.I) and _TASK_IMPERATIVE.search(text):
        return Intent.TASK, 0.88, "mixed_greeting_then_task"

    if score_task >= 0.7 and score_task > score_chat + 0.1:
        return Intent.TASK, min(0.92, score_task), "tier2_task"
    if score_chat >= 0.7 and score_chat > score_task + 0.1:
        return Intent.CHAT, min(0.92, score_chat), "tier2_chat"
    if score_task > score_chat and score_task >= 0.4:
        return Intent.AMBIGUOUS, 0.55, "tier2_lean_task"
    if score_chat > score_task and score_chat >= 0.4:
        return Intent.AMBIGUOUS, 0.55, "tier2_lean_chat"
    return Intent.AMBIGUOUS, 0.4, "tier2_unclear"


def score_complexity(prompt: str) -> float:
    """0.0–1.0 complexity for model routing."""
    text = prompt.strip()
    if not text:
        return 0.0
    tokens = max(1, len(text.split()))
    score = min(0.35, tokens / 80.0)
    tech = len(_TECH_KEYWORDS.findall(text))
    domain = len(_DOMAIN_KEYWORDS.findall(text))
    score += min(0.35, tech * 0.08 + domain * 0.06)
    depth = text.count("(") + text.count("[") + text.count("{")
    score += min(0.2, depth * 0.04)
    if _TASK_CLI.search(text) or _TASK_PATH_OR_FILE.search(text):
        score += 0.15
    return max(0.0, min(1.0, score))


def select_ollama_model(
    prompt: str,
    intent: Literal["chat", "task"] = "chat",
) -> Tuple[str, int, float]:
    """
    Returns (model_name, num_predict, timeout_seconds).
    """
    c = score_complexity(prompt)
    if intent == "chat":
        if c < 0.3:
            return "qwen2.5-coder:1.5b", 40, 12.0
        if c < 0.7:
            return "qwen2.5-coder:3b", 80, 20.0
        return "qwen2.5-coder:7b", 120, 30.0

    # task
    if c < 0.3:
        return "qwen2.5-coder:3b", 120, 25.0
    if c < 0.7:
        return "qwen2.5-coder:7b", 200, 45.0
    return "qwen2.5-coder:7b", 300, 60.0


def classify_intent(
    prompt: str,
    *,
    force_mode: Optional[str] = None,
    history: Optional[list] = None,  # reserved for multi-turn
) -> IntentResult:
    """
    Classify prompt as chat or task.

    force_mode: optional UI override ('chat' | 'task' | 'work' | 'agent' | 'auto').
    Defaults to CHAT when ambiguous (safer than accidental full pipeline).
    """
    if force_mode:
        fm = force_mode.strip().lower()
        if fm in ("chat",):
            return IntentResult("chat", Intent.CHAT, 1.0, 0, "ui_force_chat")
        if fm in ("task", "work", "agent", "code", "exec"):
            return IntentResult("task", Intent.TASK, 1.0, 0, "ui_force_task")

    t1 = _tier1(prompt)
    if t1 is not None:
        intent, conf, reason = t1
        if intent == Intent.CHAT:
            return IntentResult("chat", intent, conf, 1, reason)
        if intent == Intent.TASK:
            return IntentResult("task", intent, conf, 1, reason)

    raw, conf, reason = _tier2(prompt)
    if raw == Intent.TASK and conf >= 0.7:
        return IntentResult("task", raw, conf, 2, reason)
    if raw == Intent.CHAT and conf >= 0.7:
        return IntentResult("chat", raw, conf, 2, reason)

    # Ambiguous / low confidence → CHAT (safe default)
    if raw == Intent.TASK:
        # lean task but low conf — still prefer chat unless fairly strong
        if conf >= 0.55:
            return IntentResult("task", raw, conf, 2, reason + "_accepted")
        return IntentResult("chat", Intent.AMBIGUOUS, conf, 2, reason + "_default_chat")

    return IntentResult("chat", Intent.AMBIGUOUS if raw == Intent.AMBIGUOUS else raw, conf, 2, reason + "_default_chat")


# User-facing thought curation for task steps
_CURATION_MAP = [
    (re.compile(r"BehaviorMonitor", re.I), "thought process monitor"),
    (re.compile(r"\bRLock\b", re.I), "synchronization"),
    (re.compile(r"checkpoint[_\s-]?LSN", re.I), "progress save point"),
    (re.compile(r"telemetry\s+SLA", re.I), "response timing check"),
    (re.compile(r"PEP\s*578", re.I), "safety hooks"),
    (re.compile(r"Job\s+Object", re.I), "safe execution environment"),
    (re.compile(r"autonomous\s+execution\s+pipeline", re.I), "task analysis"),
    (re.compile(r"Initializing\s+live", re.I), "Starting"),
]


def curate_thought(internal: str, max_len: int = 120) -> str:
    """Map internal monitoring language to short user-facing text."""
    text = (internal or "").strip()
    if not text:
        return "Working on your request…"
    for pattern, repl in _CURATION_MAP:
        text = pattern.sub(repl, text)
    # Drop overly raw JSON-ish blobs
    if text.startswith("{") or text.startswith("["):
        return "Processing step results…"
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return text


STEP_USER_LABELS = {
    "initial_planning": {
        "title": "Planning",
        "details": [
            "Analyzing your request",
            "Breaking the work into clear steps",
        ],
    },
    "execution_phase": {
        "title": "Executing",
        "details": [
            "Running work in a safe environment",
            "Gathering results from tools",
        ],
    },
    "reflection_synthesis": {
        "title": "Verifying",
        "details": [
            "Checking results",
            "Preparing the final answer",
        ],
    },
}
