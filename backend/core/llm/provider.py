"""LLM provider abstraction layer.

Supports multiple LLM providers (OpenAI, Anthropic) through a common
interface. Users bring their own API keys (BYOK) and the system
routes requests to the correct provider.
"""

import logging
from abc import ABC, abstractmethod

import anthropic
import openai

from api.exceptions import LLMProviderError

logger = logging.getLogger(__name__)

# Supported provider names
SUPPORTED_PROVIDERS = {"openai", "anthropic"}


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> str:
        """Generate a completion from the LLM.

        Args:
            messages: Chat messages in OpenAI format [{"role": "...", "content": "..."}].
            model: Model identifier (e.g., "gpt-4o", "claude-sonnet-4-20250514").
            temperature: Sampling temperature. Defaults to 0.0 for deterministic legal analysis.
            max_tokens: Maximum tokens in the response.

        Returns:
            The model's response text.

        Raises:
            LLMProviderError: If the API call fails.
        """
        ...


class OpenAIProvider(LLMProvider):
    """OpenAI API provider using the official SDK."""

    def __init__(self, api_key: str) -> None:
        """Initialize with a decrypted OpenAI API key."""
        self._client = openai.AsyncOpenAI(api_key=api_key)

    async def complete(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> str:
        """Call OpenAI chat completions API."""
        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            if content is None:
                raise LLMProviderError("OpenAI returned empty response")
            return content
        except openai.AuthenticationError as exc:
            raise LLMProviderError("Invalid OpenAI API key") from exc
        except openai.RateLimitError as exc:
            raise LLMProviderError("OpenAI rate limit exceeded") from exc
        except openai.APIError as exc:
            raise LLMProviderError(f"OpenAI API error: {exc}") from exc
        except LLMProviderError:
            raise
        except Exception as exc:
            raise LLMProviderError(f"OpenAI request failed: {exc}") from exc


class AnthropicProvider(LLMProvider):
    """Anthropic API provider using the official SDK."""

    def __init__(self, api_key: str) -> None:
        """Initialize with a decrypted Anthropic API key."""
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> str:
        """Call Anthropic messages API.

        Converts OpenAI-style messages to Anthropic format:
        - Extracts system message separately (Anthropic uses a top-level system param)
        - Passes remaining messages as the messages list
        """
        try:
            # Anthropic requires system message as a separate parameter
            system_msg = None
            chat_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                else:
                    chat_messages.append(msg)

            kwargs: dict = {
                "model": model,
                "messages": chat_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if system_msg:
                kwargs["system"] = system_msg

            response = await self._client.messages.create(**kwargs)
            content = response.content[0].text
            return content
        except anthropic.AuthenticationError as exc:
            raise LLMProviderError("Invalid Anthropic API key") from exc
        except anthropic.RateLimitError as exc:
            raise LLMProviderError("Anthropic rate limit exceeded") from exc
        except anthropic.APIError as exc:
            raise LLMProviderError(f"Anthropic API error: {exc}") from exc
        except LLMProviderError:
            raise
        except Exception as exc:
            raise LLMProviderError(f"Anthropic request failed: {exc}") from exc


def get_llm_provider(api_key: str, provider_name: str) -> LLMProvider:
    """Create an LLM provider instance for the given provider name.

    Args:
        api_key: Decrypted API key for the provider.
        provider_name: Provider identifier ("openai" or "anthropic").

    Returns:
        An LLMProvider instance ready to make API calls.

    Raises:
        LLMProviderError: If the provider name is not supported.
    """
    if provider_name == "openai":
        return OpenAIProvider(api_key)
    elif provider_name == "anthropic":
        return AnthropicProvider(api_key)
    else:
        raise LLMProviderError(
            f"Unsupported LLM provider: '{provider_name}'. "
            f"Supported providers: {', '.join(sorted(SUPPORTED_PROVIDERS))}"
        )
