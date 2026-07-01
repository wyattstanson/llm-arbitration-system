"""Instructor-wrapped client factories + a unified structured-call dispatcher.

Each client's `.chat.completions.create(..., response_model=...)` yields a validated
Pydantic object instead of raw text. Ollama and Groq use JSON mode (local/open models
don't do native tool-calling as reliably as the hosted frontier models).
"""

from __future__ import annotations

import instructor

from src import config


def openai_client():
    from openai import OpenAI

    return instructor.from_openai(OpenAI(api_key=config.OPENAI_API_KEY))


def anthropic_client():
    from anthropic import Anthropic

    return instructor.from_anthropic(Anthropic(api_key=config.ANTHROPIC_API_KEY))


def groq_client():
    from openai import OpenAI

    return instructor.from_openai(
        OpenAI(base_url=config.GROQ_BASE_URL, api_key=config.GROQ_API_KEY),
        mode=instructor.Mode.JSON,
    )


def ollama_client():
    from openai import OpenAI

    return instructor.from_openai(
        OpenAI(base_url=config.OLLAMA_BASE_URL, api_key="ollama"),
        mode=instructor.Mode.JSON,
    )


def structured_call(provider: str, model: str, messages: list, response_model):
    """Dispatch one schema-validated completion to the right provider."""
    if provider == "openai":
        return openai_client().chat.completions.create(
            model=model, response_model=response_model, messages=messages, temperature=0
        )
    if provider == "anthropic":
        return anthropic_client().chat.completions.create(
            model=model, response_model=response_model, messages=messages,
            temperature=0, max_tokens=3072,
        )
    if provider == "groq":
        return groq_client().chat.completions.create(
            model=model, response_model=response_model, messages=messages,
            temperature=0, max_retries=2,
        )
    # ollama (local) — JSON mode, a couple of extra retries for the small model
    return ollama_client().chat.completions.create(
        model=model, response_model=response_model, messages=messages,
        temperature=0, max_retries=3,
    )
