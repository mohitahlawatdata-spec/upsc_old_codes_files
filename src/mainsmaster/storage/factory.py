"""Artifact storage selection."""

from mainsmaster.settings import Settings
from mainsmaster.storage.base import ArtifactStore


def artifact_store(settings: Settings) -> ArtifactStore:
    if settings.artifact_store == "s3":
        from mainsmaster.storage.s3 import S3ArtifactStore

        return S3ArtifactStore(settings)
    from mainsmaster.storage.local import LocalArtifactStore

    return LocalArtifactStore(settings.data_dir)
