"""Google Gemini sampler using the free API."""

import os
import re
import time
from typing import Optional

try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
except ImportError:
    raise ImportError(
        "google-generativeai not installed. Install with: pip install google-generativeai"
    )

from eval_harness.core.types import DecodingConfig


class GeminiSampler:
    """Sampler using Google Gemini API (free tier available)."""

    def __init__(
        self,
        model_id: str = "gemini-1.5-flash-latest",
        api_key: Optional[str] = None,
    ):
        """Initialize Gemini sampler.

        Args:
            model_id: Gemini model name (e.g., gemini-1.5-flash-latest, gemini-1.5-pro-latest)
            api_key: Google API key (or set GOOGLE_API_KEY env var)

        Free tier limits:
            - gemini-1.5-flash: 15 RPM, 1M tokens/day
            - gemini-1.5-pro: 2 RPM, 50 requests/day

        Common model names:
            - gemini-1.5-flash-latest (recommended for free tier)
            - gemini-1.5-pro-latest
            - gemini-pro
        """
        self.model_id = model_id
        api_key = api_key or os.getenv("GOOGLE_API_KEY")

        if not api_key:
            raise ValueError(
                "Google API key required. Set GOOGLE_API_KEY env var or pass api_key parameter.\n"
                "Get free key at: https://makersuite.google.com/app/apikey"
            )

        genai.configure(api_key=api_key)
        # Try using just the model name without models/ prefix
        self.model = genai.GenerativeModel(model_id)

    def generate(
        self,
        prompt: str,
        config: DecodingConfig,
        n_samples: int = 1,
        seed: Optional[int] = None,
    ) -> list[str]:
        """Generate n samples from Gemini.

        Args:
            prompt: Input prompt
            config: Decoding configuration
            n_samples: Number of samples (note: Gemini doesn't support n>1, so we loop)
            seed: Random seed (not supported by Gemini, included for compatibility)

        Returns:
            List of generated strings
        """
        generation_config = {
            "temperature": config.temperature,
            "top_p": config.top_p,
            "max_output_tokens": config.max_tokens,
        }

        results = []

        for i in range(n_samples):
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                try:
                    response = self.model.generate_content(
                        prompt,
                        generation_config=generation_config,
                    )

                    # Extract text from response
                    if response.text:
                        results.append(response.text)
                    else:
                        # Handle blocked or empty responses
                        results.append("")

                    break  # Success, exit retry loop

                except Exception as e:
                    error_str = str(e)

                    # Check if it's a rate limit error (429)
                    if "429" in error_str or "quota" in error_str.lower():
                        # Extract retry delay from error message
                        retry_match = re.search(r'retry in ([\d.]+)s', error_str)
                        if retry_match:
                            retry_delay = float(retry_match.group(1))
                        else:
                            # Default delays based on model
                            if "2.5" in self.model_id:
                                retry_delay = 12  # 5 RPM = 12s between requests
                            elif "1.5" in self.model_id:
                                retry_delay = 4   # 15 RPM = 4s between requests
                            else:
                                retry_delay = 30  # Conservative default

                        retry_count += 1
                        if retry_count < max_retries:
                            print(f"Rate limit hit. Waiting {retry_delay:.0f}s before retry {retry_count}/{max_retries}...")
                            time.sleep(retry_delay)
                        else:
                            print(f"Warning: Gemini API error after {max_retries} retries: {e}")
                            results.append("")
                    else:
                        # Non-rate-limit error, don't retry
                        print(f"Warning: Gemini API error: {e}")
                        results.append("")
                        break

            # Rate limiting: sleep between samples
            if i < n_samples - 1:
                if "2.5" in self.model_id:
                    time.sleep(12)  # 5 RPM
                elif "1.5" in self.model_id:
                    time.sleep(4)   # 15 RPM
                else:
                    time.sleep(0.5)

        return results

    def __repr__(self) -> str:
        return f"GeminiSampler(model={self.model_id})"
