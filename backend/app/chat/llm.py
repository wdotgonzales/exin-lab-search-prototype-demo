"""The answer model behind one small interface, like the embedder.

OpenAILLM calls the Responses API. Tests swap in a fake through FastAPI's
dependency override, so no AI call is ever made in CI.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from openai import OpenAI

from app.config import get_settings


@dataclass(frozen=True)
class Completion:
    text: str
    input_tokens: int
    output_tokens: int  # includes the model's reasoning tokens (billed as output)


class LLM(Protocol):
    model: str

    def complete(self, instructions: str, prompt: str) -> Completion: ...


class OpenAILLM:
    def __init__(self, api_key: str, model: str, effort: str = "low") -> None:
        self._client = OpenAI(api_key=api_key, max_retries=2, timeout=60)
        self.model = model
        self._effort = effort  # "low": quick answers; the hard work is retrieval

    def complete(self, instructions: str, prompt: str) -> Completion:
        response = self._client.responses.create(
            model=self.model,
            instructions=instructions,
            input=prompt,
            reasoning={"effort": self._effort},
            max_output_tokens=2000,
        )
        usage = response.usage
        return Completion(
            text=response.output_text,
            input_tokens=usage.input_tokens if usage else 0,
            output_tokens=usage.output_tokens if usage else 0,
        )


@lru_cache
def get_llm() -> LLM:
    settings = get_settings()
    key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else ""
    if not key:
        raise RuntimeError("The chat assistant needs OPENAI_API_KEY to be set")
    return OpenAILLM(key, settings.chat_model)
