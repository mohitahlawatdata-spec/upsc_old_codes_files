"""Provider used when OCR cleanup is intentionally disabled."""


class NoCleanupProvider:
    async def clean(self, text: str) -> str:
        return text
