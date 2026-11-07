"""Gemini implementations of cleanup, embedding, and mentor providers."""

from google import genai
from google.genai import types

from mainsmaster.prompts import RESTRUCTURE_PROMPT
from mainsmaster.providers.retry import retry_provider_call, retry_provider_call_async
from mainsmaster.settings import Settings


class GeminiCleanupProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def clean(self, text: str) -> str:
        if not self.settings.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY is missing")
        client = genai.Client(api_key=self.settings.google_api_key)
        try:
            response = await retry_provider_call_async(
                lambda: client.aio.models.generate_content(
                    model=self.settings.restructure_model,
                    contents=text,
                    config=types.GenerateContentConfig(
                        system_instruction=RESTRUCTURE_PROMPT,
                        temperature=0.2,
                    ),
                ),
                "Gemini cleanup",
            )
        finally:
            await client.aio.aclose()
        return (response.text or "").strip()


class GeminiEmbeddingProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    def embed(self, text: str) -> list[float]:
        if not self.settings.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY is missing")
        client = genai.Client(api_key=self.settings.google_api_key)
        try:
            response = retry_provider_call(
                lambda: client.models.embed_content(
                    model=self.settings.embedding_model,
                    contents=text,
                    config=types.EmbedContentConfig(
                        output_dimensionality=self.settings.embedding_dim,
                    ),
                ),
                "Gemini embedding",
            )
        finally:
            client.close()
        if not response.embeddings or response.embeddings[0].values is None:
            raise RuntimeError("Gemini returned no embedding")
        return list(response.embeddings[0].values)


class GeminiMentorProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    def answer(self, context: str, history: str, question: str) -> str:
        if not self.settings.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY is missing")
        system_prompt = (
            "You are a UPSC essay mentor. Answer only from the evaluation context. "
            "Be specific and concise. If the context does not support an answer, say so.\n\n"
            f"Evaluation context:\n{context}\n\nRecent chat:\n{history}"
        )
        client = genai.Client(api_key=self.settings.google_api_key)
        try:
            response = retry_provider_call(
                lambda: client.models.generate_content(
                    model=self.settings.mentor_model,
                    contents=question,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.2,
                    ),
                ),
                "Gemini mentor",
            )
        finally:
            client.close()
        answer = (response.text or "").strip()
        if not answer:
            raise RuntimeError("Gemini returned an empty mentor response")
        return answer
