"""Provider selection from validated settings."""

from mainsmaster.providers.base import CleanupProvider, EmbeddingProvider, MentorProvider
from mainsmaster.settings import Settings


def cleanup_provider(settings: Settings) -> CleanupProvider:
    if settings.cleanup_provider == "gemini":
        from mainsmaster.providers.gemini import GeminiCleanupProvider

        return GeminiCleanupProvider(settings)
    from mainsmaster.providers.noop import NoCleanupProvider

    return NoCleanupProvider()


def embedding_provider(settings: Settings) -> EmbeddingProvider:
    from mainsmaster.providers.gemini import GeminiEmbeddingProvider

    return GeminiEmbeddingProvider(settings)


def mentor_provider(settings: Settings) -> MentorProvider:
    from mainsmaster.providers.gemini import GeminiMentorProvider

    return GeminiMentorProvider(settings)
