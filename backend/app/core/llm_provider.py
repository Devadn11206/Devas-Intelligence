import time
import json
import re
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Type, TypeVar, get_args, get_origin
import httpx
from pydantic import BaseModel
from app.core.config import get_settings

T = TypeVar("T", bound=BaseModel)


class LLMResponse(BaseModel):
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_text(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        pass

    @abstractmethod
    async def generate_structured(
        self,
        messages: list[dict[str, str]],
        schema: Type[T],
        temperature: float = 0.0,
    ) -> T:
        pass

    @abstractmethod
    async def stream_text(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
    ) -> AsyncIterator[str]:
        pass


class OpenAICompatibleProvider(BaseLLMProvider):
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.LLM_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.LLM_API_KEY
        self.model = model or settings.LLM_MODEL_PRIMARY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def generate_text(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        start_time = time.perf_counter()
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        choice = data.get("choices", [{}])[0]
        content_val = choice.get("message", {}).get("content") or ""
        usage = data.get("usage", {})

        return LLMResponse(
            content=content_val,
            model=data.get("model", self.model),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=round(latency_ms, 2),
        )

    async def generate_structured(
        self,
        messages: list[dict[str, str]],
        schema: Type[T],
        temperature: float = 0.0,
    ) -> T:
        json_schema = json.dumps(schema.model_json_schema(), indent=2)
        system_instruction = (
            "You MUST respond ONLY with valid JSON complying exactly with this JSON Schema:\n"
            f"{json_schema}\n"
            "Do not output markdown codeblocks, notes, or any other surrounding text."
        )

        augmented_messages = [{"role": "system", "content": system_instruction}] + messages
        max_retries = 2
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                response = await self.generate_text(
                    augmented_messages, temperature=temperature, max_tokens=2048
                )
                text = response.content.strip()
                match = re.search(r"\{.*\}", text, re.DOTALL)
                if match:
                    text = match.group(0)
                data = json.loads(text)
                return schema.model_validate(data)
            except Exception as e:
                last_error = e
                augmented_messages.append({
                    "role": "user",
                    "content": f"The previous output failed validation: {str(e)}. Provide the corrected raw JSON now."
                })

        raise ValueError(f"Failed to generate valid structured response after retries: {last_error}")

    async def stream_text(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
    ) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield delta
                        except json.JSONDecodeError:
                            continue


class MockLLMProvider(BaseLLMProvider):
    def __init__(self, model: str = "mock-model"):
        self.model = model

    def _generate_mock_instance(self, schema_cls: Type[Any]) -> Any:
        if not hasattr(schema_cls, "model_fields"):
            return None

        mock_data: dict[str, Any] = {}
        for field_name, field_info in schema_cls.model_fields.items():
            annotation = field_info.annotation

            origin = get_origin(annotation)
            args = get_args(annotation)

            if origin is list:
                item_type = args[0] if args else str
                if hasattr(item_type, "model_fields"):
                    mock_data[field_name] = [self._generate_mock_instance(item_type)]
                else:
                    mock_data[field_name] = ["mock_item_1", "mock_item_2"]
            elif hasattr(annotation, "model_fields"):
                mock_data[field_name] = self._generate_mock_instance(annotation)
            elif annotation is int:
                mock_data[field_name] = 42
            elif annotation is float:
                mock_data[field_name] = 3.14
            elif annotation is bool:
                mock_data[field_name] = True
            elif annotation is str:
                mock_data[field_name] = f"mock_{field_name}_value"
            elif annotation is dict or origin is dict:
                mock_data[field_name] = {"mock_key": "mock_val"}
            else:
                mock_data[field_name] = f"mock_{field_name}"

        return schema_cls.model_validate(mock_data)

    async def generate_text(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        return LLMResponse(
            content="MOCK_RESPONSE: DEVA Intelligence Core Systems Operational.",
            model=self.model,
            prompt_tokens=10,
            completion_tokens=8,
            latency_ms=1.5,
        )

    async def generate_structured(
        self,
        messages: list[dict[str, str]],
        schema: Type[T],
        temperature: float = 0.0,
    ) -> T:
        return self._generate_mock_instance(schema)

    async def stream_text(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
    ) -> AsyncIterator[str]:
        words = ["MOCK:", "DEVA", "Intelligence", "streaming", "test", "successful."]
        for word in words:
            yield word + " "


def get_llm_provider() -> BaseLLMProvider:
    settings = get_settings()
    if settings.TESTING or settings.LLM_PROVIDER == "mock":
        return MockLLMProvider(model=settings.LLM_MODEL_PRIMARY)
    return OpenAICompatibleProvider(
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        model=settings.LLM_MODEL_PRIMARY,
    )
