"""
A tiny plugin registry.

This is the trick that keeps RAGForge feeling like ONE tool while staying made of
clean, separate pieces. Each parser, chunker, evaluator, etc. registers itself under
a name. The CLI and other code can then ask for "the structure-aware chunker" by name
without importing it directly or knowing how it's built.

Why this matters: adding a new feature later (a new chunker, a new evaluator) means
writing one new file that registers itself — you never have to edit a giant central
file. That is how you avoid the tangled-mess fate that makes big tools hard to use.

Example:
    from ragforge.core.registry import register, get, available

    @register("chunker", "fixed")
    class FixedChunker(...):
        ...

    chunker_cls = get("chunker", "fixed")
    print(available("chunker"))  # ['fixed', 'structure', ...]
"""

from __future__ import annotations

from typing import Any, Callable

# kind -> { name -> class }, e.g. {"chunker": {"fixed": FixedChunker}}
_REGISTRY: dict[str, dict[str, Any]] = {}


def register(kind: str, name: str) -> Callable[[type], type]:
    """Class decorator: register a class under a (kind, name) pair."""

    def _decorator(cls: type) -> type:
        _REGISTRY.setdefault(kind, {})
        if name in _REGISTRY[kind]:
            raise ValueError(f"{kind} named {name!r} is already registered")
        _REGISTRY[kind][name] = cls
        return cls

    return _decorator


def get(kind: str, name: str) -> Any:
    """Look up a registered class. Raises a helpful error if it's missing."""
    try:
        return _REGISTRY[kind][name]
    except KeyError:
        options = available(kind)
        raise KeyError(
            f"No {kind} named {name!r}. Available {kind}s: {options or '(none registered)'}"
        )


def available(kind: str) -> list[str]:
    """List the registered names for a kind, e.g. all chunkers."""
    return sorted(_REGISTRY.get(kind, {}).keys())


def all_kinds() -> list[str]:
    """List every kind that has at least one registered item."""
    return sorted(_REGISTRY.keys())


def registered_info() -> dict[str, list[str]]:
    """Return the full registry as a dict: {kind: [names]}. Useful for API /capabilities."""
    return {kind: sorted(names.keys()) for kind, names in sorted(_REGISTRY.items())}
