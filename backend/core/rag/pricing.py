"""LLM model pricing for token cost estimation.

Prices are per 1,000,000 (1M) tokens, matching how providers list them.
Update this dict when providers change pricing.

Last updated: 2025-03-25
"""

import math

# Pricing per 1M tokens (input and output)
MODEL_PRICING: dict[str, dict[str, float]] = {
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    # Anthropic
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-haiku-3-5-20241022": {"input": 0.80, "output": 4.00},
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
}


def get_model_pricing(model: str) -> dict[str, float] | None:
    """Look up pricing for a model.

    Tries exact match first, then prefix match (e.g., "gpt-4o" matches
    "gpt-4o-2024-08-06" if the user passes a dated variant).

    Args:
        model: Model identifier string.

    Returns:
        Dict with "input" and "output" prices per 1M tokens, or None if unknown.
    """
    # Exact match
    if model in MODEL_PRICING:
        return MODEL_PRICING[model]

    # Prefix match: check if any known model is a prefix of the requested model
    for known_model, pricing in MODEL_PRICING.items():
        if model.startswith(known_model):
            return pricing

    return None


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

    # Calculate costs (prices are per 1M tokens, round up to nearest cent)
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
