
"""Test OCR against a local image file or URL.

Usage:
  cd backend
  uv run python scripts/test_ocr.py scripts/test_bscard-1.jpg
  uv run python scripts/test_ocr.py test_bscard-1.jpg          # looks in scripts/
  uv run python scripts/test_ocr.py /full/path/to/card.jpg
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai.pipelines.ocr import extract_from_image_url, ocr_mode_debug
from app.core.config import get_settings

SCRIPTS_DIR = Path(__file__).resolve().parent


def resolve_image_path(target: str) -> Path | None:
    """Resolve local image path from several common inputs."""
    name = Path(target).name
    candidates = [
        Path(target),
        Path.cwd() / target,
        Path.cwd() / name,
        SCRIPTS_DIR / target,
        SCRIPTS_DIR / name,
    ]
    seen: set[Path] = set()
    for p in candidates:
        try:
            resolved = p.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return resolved
    return None


def _ensure_config_or_exit() -> None:
    settings = get_settings()
    mode = ocr_mode_debug()
    print(f"OCR mode: {mode}")
    print(f"  OCR_PROVIDER={settings.ocr_provider}")
    print(f"  OCR_USE_MOCK={settings.ocr_use_mock}")
    print(f"  GEMINI_API_KEY={'set' if settings.gemini_api_key else 'NOT SET'}")
    print(f"  GEMINI_OCR_MODEL={settings.gemini_ocr_model}\n")

    if settings.ocr_will_use_mock:
        print("仍在使用假資料。請在 backend/.env 加入：")
        print("  OCR_PROVIDER=gemini")
        print("  GEMINI_API_KEY=你的key")
        print("  OCR_USE_MOCK=false")
        print("\n或單次測試：")
        print("  GEMINI_API_KEY=xxx OCR_PROVIDER=gemini uv run python scripts/test_ocr.py card.jpg")
        sys.exit(1)


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/test_ocr.py <image-path-or-url>")
        print("Example: uv run python scripts/test_ocr.py scripts/test_bscard-1.jpg")
        sys.exit(1)

    _ensure_config_or_exit()
    target = sys.argv[1]

    local = resolve_image_path(target)
    if local:
        image_ref = str(local)
        print(f"File: {local}\n")
    elif target.startswith("http://") or target.startswith("https://"):
        image_ref = target
        print(f"URL: {image_ref}\n")
    else:
        print(f"找不到檔案: {target}\n")
        print("提示：若圖片在 backend/scripts/，請用：")
        print("  uv run python scripts/test_ocr.py scripts/test_bscard-1.jpg")
        print("或：")
        print("  uv run python scripts/test_ocr.py test_bscard-1.jpg")
        sys.exit(1)

    out, ms, engine, version = await extract_from_image_url(image_ref)
    print(f"Engine: {engine} {version} ({ms}ms)\n")
    print(out.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
