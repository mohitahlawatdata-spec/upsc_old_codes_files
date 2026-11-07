"""Small provider contracts used by the domain pipeline."""

from typing import Protocol


class CleanupProvider(Protocol):
    async def clean(self, text: str) -> str: ...


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]: ...


class MentorProvider(Protocol):
    def answer(self, context: str, history: str, question: str) -> str: ...
