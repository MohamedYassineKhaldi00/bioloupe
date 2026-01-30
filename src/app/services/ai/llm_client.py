"""
LLM Client using LiteLLM for universal LLM API access.

Supports all LiteLLM providers:
- OpenAI (gpt-4o, gpt-4o-mini, etc.)
- Anthropic (claude-3-5-sonnet, etc.)
- Mistral (mistral-large, etc.)
- Groq (groq/llama-3.1-70b, etc.)
- Azure, local models, and more

Reference: https://docs.litellm.ai/docs/
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import litellm

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Universal LLM client powered by LiteLLM.

    Provides async text generation with support for any LLM provider.
    """

    def __init__(
        self,
        default_model: str = "gpt-4o-mini",
        default_temperature: float = 0.7,
        default_max_tokens: int = 4000,
    ):
        """
        Initialize LLM client with default parameters.

        Args:
            default_model: Default LiteLLM model name (e.g., "gpt-4o", "claude-3-5-sonnet")
            default_temperature: Default temperature for generation (0.0 - 2.0)
            default_max_tokens: Default max tokens to generate
        """
        self.default_model = default_model
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens

        logger.info(
            "LLMClient initialized",
            extra={
                "default_model": default_model,
                "default_temperature": default_temperature,
                "default_max_tokens": default_max_tokens,
            },
        )

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_message: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate text using LLM via LiteLLM.

        Supports ALL LiteLLM providers and models through unified interface.

        Args:
            prompt: User prompt for text generation
            model: Override default model (e.g., "gpt-4o", "claude-3-5-sonnet", "groq/llama-3.1-70b")
            temperature: Override default temperature
            max_tokens: Override default max tokens
            system_message: Custom system message (default: scientific research assistant)
            extra_params: Additional LiteLLM parameters (e.g., top_p, frequency_penalty)

        Returns:
            Generated text from LLM

        Raises:
            Exception: If LLM API call fails

        Examples:
            >>> client = LLMClient()
            >>> result = await client.generate("What is CRISPR?")
            >>> result = await client.generate("Explain PCR", model="claude-3-5-sonnet")
            >>> result = await client.generate("Fast inference", model="groq/llama-3.1-70b")
        """
        model_to_use = model or self.default_model
        temperature_to_use = temperature if temperature is not None else self.default_temperature
        max_tokens_to_use = max_tokens or self.default_max_tokens

        system_msg = system_message or "You are a scientific research assistant helping biotechnology researchers."

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ]

        params = {
            "model": model_to_use,
            "messages": messages,
            "temperature": temperature_to_use,
            "max_tokens": max_tokens_to_use,
        }

        if extra_params:
            params.update(extra_params)

        try:
            logger.info(
                "Calling LLM",
                extra={
                    "model": model_to_use,
                    "temperature": temperature_to_use,
                    "max_tokens": max_tokens_to_use,
                    "prompt_length": len(prompt),
                },
            )

            response = await litellm.acompletion(**params)

            generated_text = response.choices[0].message.content

            logger.info(
                "LLM generation successful",
                extra={
                    "model": model_to_use,
                    "response_length": len(generated_text),
                    "finish_reason": response.choices[0].finish_reason,
                },
            )

            return generated_text

        except Exception as exc:
            logger.error(
                "LLM generation failed",
                extra={
                    "model": model_to_use,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
                exc_info=True,
            )
            raise

    async def generate_with_history(
        self,
        messages: list[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate text with conversation history.

        Args:
            messages: List of message dicts with "role" and "content" keys
            model: Override default model
            temperature: Override default temperature
            max_tokens: Override default max tokens
            extra_params: Additional LiteLLM parameters

        Returns:
            Generated text from LLM
        """
        model_to_use = model or self.default_model
        temperature_to_use = temperature if temperature is not None else self.default_temperature
        max_tokens_to_use = max_tokens or self.default_max_tokens

        params = {
            "model": model_to_use,
            "messages": messages,
            "temperature": temperature_to_use,
            "max_tokens": max_tokens_to_use,
        }

        if extra_params:
            params.update(extra_params)

        try:
            response = await litellm.acompletion(**params)
            return response.choices[0].message.content
        except Exception as exc:
            logger.error(
                "LLM generation with history failed",
                extra={"model": model_to_use, "error": str(exc)},
                exc_info=True,
            )
            raise
