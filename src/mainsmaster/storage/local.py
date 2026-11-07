"""Local artifact store used during development and tests."""

import shutil
from pathlib import Path


class LocalArtifactStore:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def upload_tree(self, source: Path, prefix: str) -> list[str]:
        source = source.resolve()
        destination = (self.root / prefix).resolve()
        if not destination.is_relative_to(self.root):
            raise ValueError("Artifact prefix escapes the configured storage root")
        if source.is_relative_to(self.root):
            return [
                path.relative_to(self.root).as_posix()
                for path in source.rglob("*")
                if path.is_file()
            ]
        destination.mkdir(parents=True, exist_ok=True)
        uploaded = []
        for path in source.rglob("*"):
            if path.is_file():
                target = destination / path.relative_to(source)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
                uploaded.append(target.relative_to(self.root).as_posix())
        return uploaded

    def delete_prefix(self, prefix: str) -> None:
        target = (self.root / prefix).resolve()
        if target == self.root or not target.is_relative_to(self.root):
            raise ValueError("Refusing to delete the artifact storage root")
        if target.exists():
            shutil.rmtree(target)
