"""Groq API sampler - very generous free tier (30 RPM, 14.4k/day)."""

import os
import time
from typing import Optional

try:
    from groq import Groq
except ImportError:
    raise ImportError(
        "groq not installed. Install with: pip install groq"
    )

from eval_harness.core.types import DecodingConfig


class GroqSampler:
    """Sampler using Groq API (very generous free tier).

    Free tier limits:
    - 30 requests per minute (RPM)
    - 14,400 requests per day
    - Much faster than Gemini!

    Get free API key at: https://console.groq.com/keys
    """

    def __init__(
        self,
        model_id: str = "llama-3.3-70b-versatile",
        api_key: Optional[str] = None,
    ):
        """Initialize Groq sampler.

        Args:
            model_id: Groq model name
            api_key: Groq API key (or set GROQ_API_KEY env var)

        Popular models:
            - llama-3.3-70b-versatile (recommended - best for JSON)
            - llama-3.1-70b-versatile
            - mixtral-8x7b-32768
            - gemma2-9b-it
        """
        self.model_id = model_id
        api_key = api_key or os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "Groq API key required. Set GROQ_API_KEY env var or pass api_key parameter.\n"
                "Get free key at: https://console.groq.com/keys"
            )

        self.client = Groq(api_key=api_key)

    def generate(
        self,
        prompt: str,
        config: DecodingConfig,
        n_samples: int = 1,
        seed: Optional[int] = None,
    ) -> list[str]:
        """Generate n samples from Groq.

        Args:
            prompt: Input prompt
            config: Decoding configuration
            n_samples: Number of samples
            seed: Random seed (Groq supports this!)

        Returns:
            List of generated strings
        """
        results = []

        for i in range(n_samples):
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                try:
                    # Groq uses OpenAI-compatible API
                    # Convert numpy int64 to Python int for JSON serialization
                    kwargs = {
                        "model": self.model_id,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": config.temperature,
                        "top_p": config.top_p,
                        "max_tokens": config.max_tokens,
                    }
                    if seed is not None:
                        kwargs["seed"] = int(seed)  # Convert to Python int

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
                        # Exponential backoff: 5s, 10s, 20s
                        retry_delay = 5 * (2 ** (retry_count - 1))

                        if retry_count < max_retries:
                            print(f"Rate limit hit. Waiting {retry_delay}s before retry {retry_count}/{max_retries}...")
                            time.sleep(retry_delay)
                        else:
                            print(f"Warning: Groq API error after {max_retries} retries: {e}")
                            results.append("")
                    else:
                        # Non-rate-limit error, don't retry
                        print(f"Warning: Groq API error: {e}")
                        results.append("")
                        break

            # Rate limiting: Be very conservative - 3s between requests (20 RPM)
            if i < n_samples - 1:
                time.sleep(3)

        return results

    def __repr__(self) -> str:
        return f"GroqSampler(model={self.model_id})"
