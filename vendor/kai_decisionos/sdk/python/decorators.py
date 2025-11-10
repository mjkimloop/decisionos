from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Dict


Hook = Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]


def pre_hook(hook: Hook) -> Callable[[Callable[..., Dict[str, Any]]], Callable[..., Dict[str, Any]]]:
    """Annotate a function to run before the main handler."""

    def decorator(handler: Callable[..., Dict[str, Any]]):
        setattr(handler, "__ext_pre_hook__", hook)
        return handler

    return decorator


def post_hook(hook: Hook) -> Callable[[Callable[..., Dict[str, Any]]], Callable[..., Dict[str, Any]]]:
    """Annotate a function to run after the main handler."""

    def decorator(handler: Callable[..., Dict[str, Any]]):
        setattr(handler, "__ext_post_hook__", hook)
        return handler

    return decorator


def feature(name: str) -> Callable[[Callable[..., Dict[str, Any]]], Callable[..., Dict[str, Any]]]:
    """Mark a helper function as providing a named feature."""

    def decorator(func: Callable[..., Dict[str, Any]]):
        setattr(func, "__ext_feature__", name)
        return func

    return decorator


def with_context(func: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap a handler to expose extension context."""

    @wraps(func)
    def wrapper(config: Dict[str, Any], ctx: Dict[str, Any]):
        return func(config, ctx)

    return wrapper


__all__ = ["pre_hook", "post_hook", "feature", "with_context"]
