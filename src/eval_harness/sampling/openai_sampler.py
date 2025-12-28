"""OpenAI API sampler - supports GPT-4.1 Nano and other models."""

import os
import time
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    raise ImportError(
        "openai not installed. Install with: pip install openai"
    )

from eval_harness.core.types import DecodingConfig


class OpenAISampler:
    """Sampler using OpenAI API.

    Supports all OpenAI models including GPT-4.1 Nano (cheapest option).

    Pricing (as of Jan 2025):
    - GPT-4.1 Nano: $0.10/$0.40 per million tokens (input/output)
    - GPT-4o Mini: $0.15/$0.60 per million tokens
    - GPT-4o: $2.50/$10.00 per million tokens

    Get API key at: https://platform.openai.com/api-keys
    """

    def __init__(
        self,
        model_id: str = "gpt-4.1-nano",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """Initialize OpenAI sampler.

        Args:
            model_id: OpenAI model name (default: gpt-4.1-nano)
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            base_url: Optional API base URL (for custom endpoints)

        Popular models:
            - gpt-4.1-nano (recommended - cheapest, fast, good for JSON)
            - gpt-4o-mini (slightly more expensive, very reliable)
            - gpt-4o (expensive but highest quality)
        """
        self.model_id = model_id
        api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY env var or pass api_key parameter.\n"
                "Get key at: https://platform.openai.com/api-keys"
            )

        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(
        self,
        prompt: str,
        config: DecodingConfig,
        n_samples: int = 1,
        seed: Optional[int] = None,
    ) -> list[str]:
        """Generate n samples from OpenAI.

        Args:
            prompt: Input prompt
            config: Decoding configuration
            n_samples: Number of samples
            seed: Random seed (OpenAI supports this for reproducibility)

        Returns:
            List of generated strings
        """
        results = []

        for i in range(n_samples):
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                try:
                    kwargs = {
                        "model": self.model_id,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": config.temperature,
                        "top_p": config.top_p,
                        "max_tokens": config.max_tokens,
                    }
                    if seed is not None:
                        kwargs["seed"] = int(seed)  # Convert numpy int64 to Python int

                    response = self.client.chat.completions.create(**kwargs)

                    # Extract text from response
                    if response.choices and len(response.choices) > 0:
                        content = response.choices[0].message.content
                        results.append(content if content else "")
                    else:
                        results.append("")

                    break  # Success, exit retry loop

                except Exception as e:
                    error_str = str(e)

                    # Check if it's a rate limit error
                    if "rate_limit" in error_str.lower() or "429" in error_str:
                        retry_count += 1
                        # Exponential backoff: 2s, 4s, 8s
                        retry_delay = 2 * (2 ** (retry_count - 1))

                        if retry_count < max_retries:
                            print(f"Rate limit hit. Waiting {retry_delay}s before retry {retry_count}/{max_retries}...")
                            time.sleep(retry_delay)
                        else:
                            print(f"Warning: OpenAI API error after {max_retries} retries: {e}")
                            results.append("")
                    else:
                        # Non-rate-limit error, don't retry
                        print(f"Warning: OpenAI API error: {e}")
                        results.append("")
                        break

            # Small delay between requests to be polite (OpenAI has generous rate limits)
            if i < n_samples - 1:
                time.sleep(0.1)

        return results

    def __repr__(self) -> str:
        return f"OpenAISampler(model={self.model_id})"
