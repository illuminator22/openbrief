"""LLM model pricing and supported models registry.

Prices are per 1,000,000 (1M) tokens, matching how providers list them.
Update this dict when providers change pricing.

Last updated: March 2026
"""

import math

# Pricing per 1M tokens (input and output)
MODEL_PRICING: dict[str, dict[str, float]] = {
    # OpenAI
    "gpt-5.4": {"input": 2.50, "output": 15.00},
    "gpt-5.4-mini": {"input": 0.75, "output": 4.50},
    "gpt-5.4-nano": {"input": 0.20, "output": 1.25},
    # Anthropic
    "claude-opus-4-6": {"input": 5.00, "output": 25.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    # DeepSeek
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
}

# Models available for user selection, grouped by provider
SUPPORTED_MODELS: dict[str, list[dict[str, str]]] = {
    "openai": [
        {"id": "gpt-5.4", "name": "GPT-5.4", "tier": "Premium", "description": "Best for complex analysis and full reviews"},
        {"id": "gpt-5.4-mini", "name": "GPT-5.4 Mini", "tier": "Standard", "description": "Good balance of quality and speed"},
        {"id": "gpt-5.4-nano", "name": "GPT-5.4 Nano", "tier": "Quick", "description": "Fast and affordable for quick questions"},
    ],
    "anthropic": [
        {"id": "claude-opus-4-6", "name": "Claude Opus 4.6", "tier": "Premium", "description": "Best for complex analysis and full reviews"},
        {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "tier": "Standard", "description": "Good balance of quality and speed"},
    ],
    "deepseek": [
        {"id": "deepseek-reasoner", "name": "DeepSeek R1", "tier": "Standard", "description": "Advanced reasoning at low cost"},
    ],
}

# Flat set of all valid model IDs for validation
VALID_MODEL_IDS: set[str] = {
    model["id"]
    for models in SUPPORTED_MODELS.values()
    for model in models
}


def get_model_pricing(model: str) -> dict[str, float] | None:
    """Look up pricing for a model.

    Tries exact match first, then prefix match (e.g., "gpt-5.4" matches
    "gpt-5.4-2026-03-01" if the user passes a dated variant).

    Args:
        model: Model identifier string.

    Returns:
        Dict with "input" and "output" prices per 1M tokens, or None if unknown.
    """
    if model in MODEL_PRICING:
        return MODEL_PRICING[model]

    for known_model, pricing in MODEL_PRICING.items():
        if model.startswith(known_model):
            return pricing

    return None


def get_supported_models_with_pricing() -> dict[str, list[dict]]:
    """Return supported models with pricing information attached.

    Returns:
        Dict grouped by provider, each model includes id, name, description,
        and pricing (input/output per 1M tokens).
    """
    result: dict[str, list[dict]] = {}
    for provider, models in SUPPORTED_MODELS.items():
        result[provider] = []
        for model in models:
            pricing = get_model_pricing(model["id"])
            result[provider].append({
                **model,
                "pricing": pricing,
            })
    return result


def estimate_cost(
    input_tokens: int,
    estimated_output_tokens: int,
    model: str,
) -> dict:
    """Estimate the API cost for a given token count.

    Args:
        input_tokens: Number of input/prompt tokens.
        estimated_output_tokens: Estimated number of output/completion tokens.
        model: Model identifier string.

    Returns:
        Dict with: input_tokens, estimated_output_tokens, model,
        input_cost, output_cost, total_estimated_cost, pricing_available.
        Costs are in USD, rounded up to the nearest cent for safety.
        If model not in pricing table, costs are None and pricing_available=False.
    """
    pricing = get_model_pricing(model)

    if pricing is None:
        return {
            "input_tokens": input_tokens,
            "estimated_output_tokens": estimated_output_tokens,
            "model": model,
            "input_cost": None,
            "output_cost": None,
            "total_estimated_cost": None,
            "pricing_available": False,
        }

    input_cost = math.ceil(input_tokens * pricing["input"] / 1_000_000 * 100) / 100
    output_cost = math.ceil(estimated_output_tokens * pricing["output"] / 1_000_000 * 100) / 100
    total_cost = round(input_cost + output_cost, 2)

    return {
        "input_tokens": input_tokens,
        "estimated_output_tokens": estimated_output_tokens,
        "model": model,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_estimated_cost": total_cost,
        "pricing_available": True,
    }
