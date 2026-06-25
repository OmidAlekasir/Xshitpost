import os
import time
from google import genai
from google.genai import types
from google.genai.errors import APIError


class AIClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        self.client = genai.Client(api_key=self.api_key)

        # Ordered list of models to try (from newest to oldest, or cheapest to most expensive)
        self.model_priority = [
            "gemini-3.5-flash",  # your current, might be overloaded
            "gemini-3.1-flash-lite",  # reliable fallback
            "gemini-2.5-flash",  # even lighter, if available
            "gemini-2.5-flash-lite",  # even lighter, if available
        ]

    def generate(
        self, prompt: str, system_instruction: str = None, retries_per_model: int = 2
    ) -> dict:
        """
        Try each model in priority order, with retries per model.
        Returns dict with 'success' and 'content' or 'error'.
        """
        last_error = None

        for model_name in self.model_priority:
            print(f"[INFO] Attempting model: {model_name}")
            for attempt in range(retries_per_model):
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=[prompt],
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                        ),
                    )
                    print(f"[SUCCESS] Model {model_name} succeeded.")
                    return {"success": True, "content": response.text.strip()}

                except APIError as e:
                    last_error = str(e)
                    print(
                        f"[WARNING] {model_name} error (attempt {attempt + 1}/{retries_per_model}): {e}"
                    )

                    # If it's a quota/overload error, wait and retry
                    if (
                        "503" in str(e)
                        or "429" in str(e)
                        or "overloaded" in str(e).lower()
                    ):
                        wait = (attempt + 1) * 5
                        print(f"[INFO] Waiting {wait}s before retry...")
                        time.sleep(wait)
                    else:
                        # Non‑retryable error – break out of retry loop for this model
                        break

                except Exception as e:
                    last_error = str(e)
                    print(f"[ERROR] Unexpected error with {model_name}: {e}")
                    break

            # If we get here, all retries for this model failed; move to next model
            print(f"[INFO] Model {model_name} failed, trying next...")

        # All models exhausted
        return {
            "success": False,
            "error": f"All models failed. Last error: {last_error}",
        }
