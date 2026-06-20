"""
LLM providers for answer generation.

This module turns RAGForge from "retrieve relevant chunks" into "retrieve + generate
a grounded answer with sources." The generation layer is OPTIONAL — retrieval-only
still works with zero LLM configured.

Architecture:
    LLMProvider (ABC)
    ├── OpenAIProvider    — gpt-4o-mini via OPENAI_API_KEY [openai extra]
    ├── AnthropicProvider — claude-3-haiku via ANTHROPIC_API_KEY [anthropic extra]
    └── OllamaProvider   — local models via http://localhost:11434 [no key needed]

Each provider registers under kind "llm" so it's discoverable via the registry
and /capabilities endpoint.

Usage:
    from ragforge.pipeline.generation import get_llm

    llm = get_llm("ollama")  # or "openai", "anthropic"
    answer = llm.generate("What is 2+2?")
"""

from __future__ import annotations

import abc
from typing import Any

from ragforge.core.registry import register, get as registry_get


class LLMProvider(abc.ABC):
    """
    Base class for LLM providers.

    Subclass this, implement generate(), and register via:
        @register("llm", "my-provider")
    """

    @abc.abstractmethod
    def generate(self, prompt: str, **opts: Any) -> str:
        """
        Generate a completion for the given prompt.

        Args:
            prompt: The full prompt string (system + user context + question).
            **opts: Provider-specific options (temperature, max_tokens, etc.)

        Returns:
            The generated text response.
        """
        ...

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable name (e.g. 'gpt-4o-mini', 'claude-3-haiku')."""
        ...


# ---------------------------------------------------------------------------
# OpenAI Provider
# ---------------------------------------------------------------------------


@register("llm", "openai")
class OpenAIProvider(LLMProvider):
    """
    OpenAI chat completions (GPT-4o-mini by default).

    Requires: OPENAI_API_KEY environment variable.
    Install: pip install ragforge[openai]
    """

    def __init__(self, model: str = "gpt-4o-mini", **kwargs: Any) -> None:
        import os

        try:
            import openai  # noqa: F401
        except ImportError:
            raise ImportError(
                "The 'openai' package is required for the OpenAI LLM provider.\n"
                "Install with:  pip install ragforge[openai]\n"
                "Or directly:   pip install openai"
            )

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set.\n"
                "Set it with:  export OPENAI_API_KEY='sk-...'"
            )

        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, **kwargs)
        self._model = model

    @property
    def name(self) -> str:
        return self._model

    def generate(self, prompt: str, **opts: Any) -> str:
        """Generate via OpenAI chat completions API."""
        temperature = opts.get("temperature", 0.2)
        max_tokens = opts.get("max_tokens", 1024)

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Anthropic Provider
# ---------------------------------------------------------------------------


@register("llm", "anthropic")
class AnthropicProvider(LLMProvider):
    """
    Anthropic Claude models (claude-3-5-haiku by default).

    Requires: ANTHROPIC_API_KEY environment variable.
    Install: pip install ragforge[anthropic]
    """

    def __init__(self, model: str = "claude-3-5-haiku-20241022", **kwargs: Any) -> None:
        import os

        try:
            import anthropic  # noqa: F401
        except ImportError:
            raise ImportError(
                "The 'anthropic' package is required for the Anthropic LLM provider.\n"
                "Install with:  pip install ragforge[anthropic]\n"
                "Or directly:   pip install anthropic"
            )

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set.\n"
                "Set it with:  export ANTHROPIC_API_KEY='sk-ant-...'"
            )

        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key, **kwargs)
        self._model = model

    @property
    def name(self) -> str:
        return self._model

    def generate(self, prompt: str, **opts: Any) -> str:
        """Generate via Anthropic messages API."""
        temperature = opts.get("temperature", 0.2)
        max_tokens = opts.get("max_tokens", 1024)

        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        # Response content is a list of content blocks
        return response.content[0].text if response.content else ""


# ---------------------------------------------------------------------------
# Ollama Provider (local, no API key needed)
# ---------------------------------------------------------------------------


@register("llm", "ollama")
class OllamaProvider(LLMProvider):
    """
    Local LLM via Ollama (http://localhost:11434).

    No API key required — just have Ollama running with a model pulled.
    Default model: llama3. Install Ollama from https://ollama.ai

    Only needs the standard library (urllib) — no extra pip packages.
    """

    def __init__(
        self,
        model: str = "llama3",
        base_url: str = "http://localhost:11434",
        **kwargs: Any,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")

    @property
    def name(self) -> str:
        return f"ollama/{self._model}"

    def generate(self, prompt: str, **opts: Any) -> str:
        """Generate via Ollama's /api/generate endpoint (streaming disabled)."""
        import json
        import urllib.request
        import urllib.error

        temperature = opts.get("temperature", 0.2)

        payload = json.dumps({
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self._base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "")
        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Could not connect to Ollama at {self._base_url}.\n"
                f"Make sure Ollama is running:  ollama serve\n"
                f"And you have a model pulled:  ollama pull {self._model}\n"
                f"Error: {e}"
            )


# ---------------------------------------------------------------------------
# Helper: resolve an LLM provider by name
# ---------------------------------------------------------------------------


def get_llm(name: str, **kwargs: Any) -> LLMProvider:
    """
    Get an LLM provider by registry name.

    Args:
        name: Provider name — "openai", "anthropic", or "ollama".
        **kwargs: Passed to the provider constructor (e.g. model="gpt-4o").

    Returns:
        An initialized LLMProvider instance.

    Raises:
        KeyError: If the provider name isn't registered.
        ImportError: If the required package isn't installed.
        ValueError: If required env vars (API keys) aren't set.
    """
    cls = registry_get("llm", name)
    return cls(**kwargs)


# ---------------------------------------------------------------------------
# Grounded prompt construction
# ---------------------------------------------------------------------------

GROUNDED_PROMPT_TEMPLATE = """You are a helpful assistant that answers questions based ONLY on the provided context.

RULES:
- Answer ONLY using information from the context below.
- If the answer is not in the context, say exactly: "I don't have enough information to answer that."
- Do NOT make up information or use knowledge outside the provided context.
- Cite which source(s) you used by referencing [Source N] numbers.
- Be concise and direct.

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""


def build_grounded_prompt(question: str, chunks: list[dict[str, Any]]) -> str:
    """
    Build a grounded-answer prompt from retrieved chunks.

    Each chunk is numbered as [Source N] so the model can cite them.
    Includes the chunk text and its source metadata.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("metadata", {}).get("source", chunk.get("doc_id", "unknown"))
        section = chunk.get("metadata", {}).get("section", "")
        label = f"[Source {i}]"
        if section:
            label += f" (section: {section})"
        label += f" from {source}"
        context_parts.append(f"{label}:\n{chunk['text']}")

    context = "\n\n---\n\n".join(context_parts)
    return GROUNDED_PROMPT_TEMPLATE.format(context=context, question=question)
