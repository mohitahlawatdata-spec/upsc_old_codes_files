"""Generate embeddings through the configured provider."""

from mainsmaster.diagnostics import stage
from mainsmaster.providers.base import EmbeddingProvider
from mainsmaster.providers.factory import embedding_provider
from mainsmaster.settings import Settings, get_settings


def embed(
    text: str,
    settings: Settings | None = None,
    provider: EmbeddingProvider | None = None,
) -> list[float]:
    selected_settings = settings or get_settings()
    selected_provider = provider or embedding_provider(selected_settings)
    with stage("Embedding encode"):
        vector = selected_provider.embed(text)
    expected = selected_settings.embedding_dim
    if len(vector) != expected:
        raise ValueError(f"Embedding has {len(vector)} dimensions; expected {expected}")
    return vector
