import json
import logging
import re
from typing import Any, Dict, Optional

from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_markdown_fences(text: str) -> str:
    return _FENCE_RE.sub("", text).strip()


class LLMService:
    def __init__(self, api_key: str, model: str = "gemini-2.5-pro", temperature: float = 0.6):
        self._llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=temperature,
        )

    def invoke(self, prompt: str) -> str:
        response = self._llm.invoke(prompt)
        return response.content.strip()

    def invoke_json(self, prompt: str, max_attempts: int = 3) -> Optional[Dict[str, Any]]:
        last_error: Optional[Exception] = None
        for attempt in range(1, max_attempts + 1):
            try:
                raw = self.invoke(prompt)
                cleaned = _strip_markdown_fences(raw)
                return json.loads(cleaned)
            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                logger.warning("LLM JSON parse failed on attempt %s: %s", attempt, e)
                prompt = (
                    prompt
                    + "\n\nYour previous response was not valid JSON. "
                    "Reply with ONLY the JSON object, no markdown, no commentary."
                )
        logger.error("LLM JSON parse exhausted retries: %s", last_error)
        return None
