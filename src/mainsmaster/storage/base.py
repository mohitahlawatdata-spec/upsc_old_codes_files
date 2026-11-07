"""Artifact storage contract."""

from pathlib import Path
from typing import Protocol


class ArtifactStore(Protocol):
    def upload_tree(self, source: Path, prefix: str) -> list[str]: ...

    def delete_prefix(self, prefix: str) -> None: ...
