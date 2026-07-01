"""Central configuration + provider auto-detection.

Design goal: the system runs with *zero* keys today (every critic falls back to
local Ollama) and silently upgrades to the real three-model architecture the
moment OPENAI_API_KEY / ANTHROPIC_API_KEY appear in the environment.

Three ways a critic ends up on local Llama instead of its hosted model:
  1. ARBITRATION_MODE=local_only  -> force ALL critics local (key-free reviewer mode).
  2. The critic's API key is missing -> that one critic falls back, others stay hosted.
  3. (Completeness critic is always local by design.)
"""

import os

from dotenv import load_dotenv

load_dotenv()

# --- Model identifiers -------------------------------------------------------
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
# Two DIFFERENT Groq models so accuracy vs logic stay genuinely diverse.
GROQ_ACCURACY_MODEL = os.getenv("GROQ_ACCURACY_MODEL", "llama-3.3-70b-versatile")
GROQ_LOGIC_MODEL = os.getenv("GROQ_LOGIC_MODEL", "qwen/qwen3-32b")  # Qwen — different vendor from Meta

# --- Endpoints / keys --------------------------------------------------------
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or ""
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") or ""
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or ""

# --- Mode --------------------------------------------------------------------
ARBITRATION_MODE = os.getenv("ARBITRATION_MODE", "auto").lower()  # "auto" | "local_only"


def local_only() -> bool:
    return ARBITRATION_MODE == "local_only"


def openai_available() -> bool:
    """True if the accuracy critic can use the real GPT-4o."""
    return not local_only() and bool(OPENAI_API_KEY)


def anthropic_available() -> bool:
    """True if the logic critic can use the real Claude."""
    return not local_only() and bool(ANTHROPIC_API_KEY)


def groq_available() -> bool:
    """True if Groq (OpenAI-compatible, hosted open models) can be used."""
    return not local_only() and bool(GROQ_API_KEY)


def resolve_accuracy() -> tuple[str, str]:
    """(provider, model) for the accuracy critic. Priority: OpenAI > Groq > local."""
    if openai_available():
        return "openai", OPENAI_MODEL
    if groq_available():
        return "groq", GROQ_ACCURACY_MODEL
    return "ollama", OLLAMA_MODEL


def resolve_logic() -> tuple[str, str]:
    """(provider, model) for the logic critic. Priority: Anthropic > Groq > local."""
    if anthropic_available():
        return "anthropic", ANTHROPIC_MODEL
    if groq_available():
        return "groq", GROQ_LOGIC_MODEL
    return "ollama", OLLAMA_MODEL


def resolve_adjudicator() -> tuple[str, str]:
    """(provider, model) for the adjudicator. Prefer the strongest available."""
    if openai_available():
        return "openai", OPENAI_MODEL
    if anthropic_available():
        return "anthropic", ANTHROPIC_MODEL
    if groq_available():
        return "groq", GROQ_ACCURACY_MODEL  # the larger general model
    return "ollama", OLLAMA_MODEL


def _label(resolved: tuple[str, str]) -> str:
    provider, model = resolved
    tag = {"openai": "", "anthropic": "", "groq": " (groq)", "ollama": " (local)"}[provider]
    return f"{model}{tag}"


def provider_summary() -> dict:
    """Human-readable map of which model each critic will actually use this run."""
    return {
        "accuracy": _label(resolve_accuracy()),
        "logic": _label(resolve_logic()),
        "completeness": f"{OLLAMA_MODEL} (local)",
        "adjudicator": _label(resolve_adjudicator()),
        "mode": ARBITRATION_MODE,
    }
