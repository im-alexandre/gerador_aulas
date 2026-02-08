from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config.paths import APP_DIR


PRICING_PATH = APP_DIR / "config" / "openai_pricing.json"
_PRICING_CACHE: dict[str, Any] | None = None


def load_pricing() -> dict[str, Any]:
    global _PRICING_CACHE
    if _PRICING_CACHE is not None:
        return _PRICING_CACHE
    if PRICING_PATH.exists():
        _PRICING_CACHE = json.loads(PRICING_PATH.read_text(encoding="utf-8"))
    else:
        _PRICING_CACHE = {}
    return _PRICING_CACHE


def compute_llm_cost(
    model: str,
    usage: dict[str, int] | None,
) -> dict[str, Any]:
    """Retorna dict com tokens e custo estimado."""
    usage = usage or {}
    pricing = load_pricing()
    model_rates = (pricing.get("models") or {}).get(model, {})
    prompt_rate = float(model_rates.get("prompt_per_1k", 0))
    prompt_cached_rate = float(model_rates.get("prompt_cached_per_1k", 0))
    completion_rate = float(model_rates.get("completion_per_1k", 0))

    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    prompt_cached_tokens = int(usage.get("prompt_cached_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))

    cost = (prompt_tokens / 1000.0) * prompt_rate
    cost += (prompt_cached_tokens / 1000.0) * prompt_cached_rate
    cost += (completion_tokens / 1000.0) * completion_rate

    return {
        "model": model,
        "prompt_tokens": prompt_tokens,
        "prompt_cached_tokens": prompt_cached_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cost_usd": round(cost, 6),
    }


def compute_image_cost(model: str, size: str, count: int) -> dict[str, Any]:
    """Retorna dict com quantidade e custo estimado de imagens."""
    pricing = load_pricing()
    image_rates = (pricing.get("images") or {}).get(model, {})
    rate = float(image_rates.get(size, 0))
    cost = count * rate
    return {
        "model": model,
        "size": size,
        "count": count,
        "cost_usd": round(cost, 6),
    }
