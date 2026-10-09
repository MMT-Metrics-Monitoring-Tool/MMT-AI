from collections.abc import Iterator
from dataclasses import dataclass, field
from openai import OpenAI

import json
import os
import time


@dataclass
class StreamResult:
    """Filled in while an answer streams, read once the stream has ended."""
    text: str = ""
    first_token_ms: int | None = None
    total_ms: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    finish_reason: str | None = None  # "length" means the answer was cut off by max_tokens


@dataclass
class LLMClient:
    """Thin wrapper over any OpenAI-compatible chat completions API (Aviary, vLLM, OpenAI, ...)."""
    model: str
    client: OpenAI
    temperature: float = 0.3
    max_tokens: int = 4000
    extra_body: dict = field(default_factory=dict)

    def stream(self, messages: list[dict[str, str]], result: StreamResult) -> Iterator[str]:
        """Streams the answer text. Timing and token usage are written into `result`."""
        start = time.monotonic()
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
            stream_options={"include_usage": True},
            extra_body=self.extra_body or None,
        )
        for chunk in stream:
            if chunk.usage:
                result.prompt_tokens = chunk.usage.prompt_tokens
                result.completion_tokens = chunk.usage.completion_tokens
            if not chunk.choices:
                continue
            if chunk.choices[0].finish_reason:
                result.finish_reason = chunk.choices[0].finish_reason
            text = chunk.choices[0].delta.content
            if text:
                if result.first_token_ms is None:
                    result.first_token_ms = int((time.monotonic() - start) * 1000)
                result.text += text
                yield text
        result.total_ms = int((time.monotonic() - start) * 1000)

    def ping(self) -> None:
        """Checks that the API is reachable and the key is accepted. Lists models, so no tokens are used."""
        self.client.models.list()


def build_llm_client() -> LLMClient:
    """
    Factory: builds the LLM client from the environment.
    LLM_EXTRA_BODY passes provider-specific options as JSON,
    e.g. {"chat_template_kwargs": {"enable_thinking": false}} for Qwen models on vLLM.
    """
    return LLMClient(
        model=os.environ["MODEL_NAME"],
        client=OpenAI(base_url=os.environ["API_BASE_URL"], api_key=os.environ["API_KEY"], timeout=120),
        temperature=float(os.getenv("LLM_TEMPERATURE", 0.3)),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", 4000)),
        extra_body=json.loads(os.getenv("LLM_EXTRA_BODY") or "{}"),
    )
