"""Concurrent Gemini OCR with an explicit all-pages-success policy."""

import asyncio
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

from mainsmaster.diagnostics import logger, stage
from mainsmaster.prompts import OCR_PROMPT
from mainsmaster.settings import Settings


@dataclass(frozen=True)
class OCRResult:
    question: str
    answer: str
    input_tokens: int
    output_tokens: int
    page_texts: list[str]


def _image_bytes(path: Path, max_width: int = 1200) -> bytes:
    with Image.open(path) as image:
        image = image.convert("RGB")
        if image.width > max_width:
            new_height = round(image.height * max_width / image.width)
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
        output = BytesIO()
        image.save(output, format="JPEG", quality=90)
        return output.getvalue()


async def extract_pages(paths: list[Path], settings: Settings) -> OCRResult:
    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY is missing")
    if not paths:
        raise ValueError("No PDF pages were rendered")
    client = genai.Client(api_key=settings.google_api_key)
    semaphore = asyncio.Semaphore(6)

    async def extract_one(path: Path) -> tuple[str, int, int]:
        with stage(f"OCR prepare image {path.name}"):
            image = _image_bytes(path)
        delay = 1.0
        async with semaphore:
            started = time.monotonic()
            logger.info("OCR START %s", path.name)
            for attempt in range(5):
                try:
                    with stage(f"OCR API {path.name} attempt {attempt + 1}"):
                        response = await client.aio.models.generate_content(
                            model=settings.ocr_model,
                            contents=[
                                OCR_PROMPT,
                                types.Part.from_bytes(data=image, mime_type="image/jpeg"),
                            ],
                            config=types.GenerateContentConfig(temperature=0),
                        )
                    if not response.text or not response.text.strip():
                        raise RuntimeError("Gemini returned empty OCR text")
                    usage = response.usage_metadata
                    logger.info("OCR DONE %s in %.1fs", path.name, time.monotonic() - started)
                    return (
                        response.text.strip(),
                        int(getattr(usage, "prompt_token_count", 0) or 0),
                        int(getattr(usage, "candidates_token_count", 0) or 0),
                    )
                except Exception as exc:
                    transient = any(
                        code in str(exc).lower() for code in ("429", "503", "rate", "timeout")
                    )
                    if attempt == 4 or not transient:
                        logger.error(
                            "OCR FAILED %s after %.1fs", path.name, time.monotonic() - started
                        )
                        raise RuntimeError(f"OCR failed on {path.name}: {exc}") from exc
                    logger.warning("OCR RETRY %s attempt %d", path.name, attempt + 2)
                    await asyncio.sleep(delay)
                    delay *= 2
        raise RuntimeError("OCR retry loop exhausted")

    try:
        results = await asyncio.gather(*(extract_one(path) for path in paths))
    finally:
        await client.aio.aclose()
    page_texts = [result[0] for result in results]
    first = page_texts[0].split("\n\n", 1)
    question = first[0].strip() if len(first) == 2 else "Topic not specified"
    body = [first[1] if len(first) == 2 else page_texts[0], *page_texts[1:]]
    return OCRResult(
        question=question,
        answer="\n\n".join(body),
        input_tokens=sum(result[1] for result in results),
        output_tokens=sum(result[2] for result in results),
        page_texts=page_texts,
    )
