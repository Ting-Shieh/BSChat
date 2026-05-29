import base64
import json
import time
from pathlib import Path

import httpx

from app.ai.schemas.ocr_output import OcrOutput
from app.core.config import get_settings

settings = get_settings()

OCR_PROMPT = """Extract business card fields from this image. Return JSON only:
{
  "name": string|null,
  "company": string|null,
  "title": string|null,
  "phones": string[],
  "emails": string[],
  "address": string|null,
  "website": string|null,
  "raw_text": string,
  "field_confidences": { "name": 0-1, "company": 0-1, "title": 0-1, ... }
}
Use Traditional Chinese when appropriate. Confidence 0-1 per field."""


def _mock_ocr() -> OcrOutput:
    return OcrOutput(
        name="王小明",
        company="ABC Tech Co.",
        title="業務經理",
        phones=["0912-345-678"],
        emails=["wang@abc.com"],
        address="台北市信義區",
        website="https://abc-tech.com.tw",
        raw_text="王小明 / ABC Tech / 業務經理",
        field_confidences={"name": 0.92, "company": 0.85, "title": 0.78, "phones": 0.9, "emails": 0.88},
    )


def _parse_json_response(text: str) -> OcrOutput:
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    parsed = json.loads(text.strip())
    return OcrOutput.model_validate(parsed)


async def _load_image_bytes(image_url: str) -> tuple[bytes, str]:
    # Local filesystem path (CLI / dev)
    local = Path(image_url)
    if local.exists() and local.is_file():
        data = local.read_bytes()
        ext = local.suffix.lower()
        media_type = "image/png" if ext == ".png" else "image/jpeg"
        return data, media_type

    if "/uploads/" in image_url:
        rel = image_url.split("/uploads/", 1)[1]
        path = Path(settings.local_upload_dir) / rel
        data = path.read_bytes()
        ext = path.suffix.lower()
        media_type = "image/png" if ext == ".png" else "image/jpeg"
        return data, media_type

    async with httpx.AsyncClient() as client:
        resp = await client.get(image_url)
        resp.raise_for_status()
        media_type = resp.headers.get("content-type", "image/jpeg")
        return resp.content, media_type


def ocr_mode_debug() -> str:
    if settings.ocr_use_mock:
        return "mock (OCR_USE_MOCK=true)"
    provider = settings.effective_ocr_provider
    if provider == "gemini" and not settings.gemini_api_key:
        return "mock (OCR_PROVIDER=gemini 但 GEMINI_API_KEY 未設定)"
    if provider == "claude" and not settings.anthropic_api_key:
        return "mock (OCR_PROVIDER=claude 但 ANTHROPIC_API_KEY 未設定)"
    if provider == "mock":
        return "mock (未設定 GEMINI_API_KEY / ANTHROPIC_API_KEY)"
    return f"live ({provider})"


async def extract_from_image_url(image_url: str) -> tuple[OcrOutput, int, str, str]:
    """Returns (output, duration_ms, engine, engine_version)."""
    start = time.monotonic()

    if settings.ocr_will_use_mock:
        await _sleep_mock()
        out = _mock_ocr()
        return out, int((time.monotonic() - start) * 1000), "mock-ocr", "1.0"

    provider = settings.effective_ocr_provider
    if provider == "gemini":
        out = await _gemini_vision(image_url)
        engine = "gemini-vision"
        version = settings.gemini_ocr_model
    else:
        out = await _claude_vision(image_url)
        engine = "claude-vision"
        version = settings.ocr_model

    return out, int((time.monotonic() - start) * 1000), engine, version


async def _sleep_mock() -> None:
    import asyncio

    await asyncio.sleep(0.8)


async def _gemini_vision(image_url: str) -> OcrOutput:
    data, media_type = await _load_image_bytes(image_url)
    b64 = base64.standard_b64encode(data).decode()

    model = settings.gemini_ocr_model
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": OCR_PROMPT},
                    {"inline_data": {"mime_type": media_type, "data": b64}},
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1,
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            url,
            params={"key": settings.gemini_api_key},
            json=payload,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text[:500]}")
        body = resp.json()

    try:
        text = body["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected Gemini response: {body}") from exc

    return _parse_json_response(text)


async def _claude_vision(image_url: str) -> OcrOutput:
    from anthropic import AsyncAnthropic

    data, media_type = await _load_image_bytes(image_url)
    b64 = base64.standard_b64encode(data).decode()
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    message = await client.messages.create(
        model=settings.ocr_model,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                    {"type": "text", "text": OCR_PROMPT},
                ],
            }
        ],
    )
    text = message.content[0].text if message.content else "{}"
    return _parse_json_response(text)
