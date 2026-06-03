"""Resolve digital business card URLs / QR payloads with SSRF protection."""

import ipaddress
import socket
from urllib.parse import urlparse

import httpx

from app.ai.pipelines.url_import_extract import extract_contact_fallback, extract_contact_from_html
from app.core.config import get_settings
from app.modules.m2_capture.import_normalize import normalize_import_fields
from app.modules.m2_capture.structured_html import parse_json_ld_contact
from app.modules.m2_capture.vcard_parser import parse_vcard

settings = get_settings()

MAX_BODY_BYTES = 512_000
MAX_IMAGE_BYTES = 5_000_000
FETCH_TIMEOUT = 8.0
FETCH_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BSChat/1.0; +digital-card-import)"}


class ImportResolveError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _is_private_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return bool(
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
    )


def _validate_public_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise ImportResolveError("UNSUPPORTED_URL", "僅支援 http/https 連結")
    if not parsed.hostname:
        raise ImportResolveError("UNSUPPORTED_URL", "無效的 URL")

    host = parsed.hostname.lower()
    if host in ("localhost", "127.0.0.1", "0.0.0.0") or host.endswith(".local"):
        raise ImportResolveError("UNSUPPORTED_URL", "不支援的網址")

    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise ImportResolveError("UNSUPPORTED_URL", "無法解析網址") from exc

    for info in infos:
        ip = info[4][0]
        if _is_private_ip(ip):
            raise ImportResolveError("UNSUPPORTED_URL", "不支援的網址")

    return parsed.geturl()


def _looks_like_vcard(content: str, content_type: str | None) -> bool:
    if content_type and "vcard" in content_type.lower():
        return True
    return "BEGIN:VCARD" in content.upper()


async def _finalize_html_result(result: dict, html: str, page_url: str) -> dict:
    result["fields"] = normalize_import_fields(
        result["fields"],
        html_text=html,
        page_url=page_url,
    )
    if not any(
        [
            result["fields"].get("name"),
            result["fields"].get("company"),
            result["fields"].get("phones"),
            result["fields"].get("emails"),
        ]
    ):
        raise ImportResolveError("IMPORT_FAILED", "無法解析此連結")
    return result


async def _parse_html_contact(html: str, page_url: str) -> dict:
    """Layered vendor-neutral HTML import (DDR-74)."""
    json_ld = parse_json_ld_contact(html)
    if json_ld:
        json_ld["raw_text"] = html[:8000]
        return await _finalize_html_result(json_ld, html, page_url)

    if settings.import_will_use_llm:
        try:
            result = await extract_contact_from_html(html, page_url)
            return await _finalize_html_result(result, html, page_url)
        except Exception as exc:
            if settings.debug:
                raise ImportResolveError("IMPORT_FAILED", f"LLM 解析失敗: {exc}") from exc

    try:
        result = extract_contact_fallback(html, page_url)
        return await _finalize_html_result(result, html, page_url)
    except ValueError as exc:
        raise ImportResolveError(
            "IMPORT_FAILED",
            "無法解析此連結；請確認 GEMINI_API_KEY 已設定，或改用手動新增",
        ) from exc


async def download_card_image(url: str) -> tuple[bytes, str]:
    """Fetch remote card image; returns (bytes, extension)."""
    safe_url = _validate_public_url(url)
    async with httpx.AsyncClient(follow_redirects=True, timeout=FETCH_TIMEOUT) as client:
        try:
            resp = await client.get(safe_url, headers=FETCH_HEADERS)
        except httpx.HTTPError as exc:
            raise ImportResolveError("IMPORT_FAILED", "無法下載名片圖片") from exc

    if resp.status_code >= 400:
        raise ImportResolveError("IMPORT_FAILED", "無法下載名片圖片")

    data = resp.content[:MAX_IMAGE_BYTES]
    if len(data) < 100:
        raise ImportResolveError("IMPORT_FAILED", "名片圖片無效")

    content_type = (resp.headers.get("content-type") or "").lower()
    if "png" in content_type:
        ext = "png"
    elif "webp" in content_type:
        ext = "webp"
    else:
        ext = "jpg"
    return data, ext


async def fetch_url(url: str) -> dict:
    safe_url = _validate_public_url(url)
    async with httpx.AsyncClient(follow_redirects=True, timeout=FETCH_TIMEOUT) as client:
        try:
            resp = await client.get(safe_url, headers=FETCH_HEADERS)
        except httpx.HTTPError as exc:
            raise ImportResolveError("IMPORT_FAILED", "無法取得連結內容") from exc

    if resp.status_code >= 400:
        raise ImportResolveError("IMPORT_FAILED", f"連結回應錯誤 ({resp.status_code})")

    content_type = resp.headers.get("content-type", "")
    body = resp.content[:MAX_BODY_BYTES]
    text = body.decode(resp.encoding or "utf-8", errors="replace")

    path_lower = urlparse(safe_url).path.lower()
    if _looks_like_vcard(text, content_type) or path_lower.endswith(".vcf"):
        try:
            parsed = parse_vcard(text)
            parsed["resolver_type"] = "vcard_url"
            return parsed
        except ValueError as exc:
            raise ImportResolveError("IMPORT_FAILED", "vCard 格式無法解析") from exc

    return await _parse_html_contact(text, safe_url)


def resolve_qr_payload(payload: str) -> dict:
    """Sync resolve for inline vCard QR content."""
    text = payload.strip()
    if not text:
        raise ImportResolveError("IMPORT_FAILED", "QR 內容為空")
    if "BEGIN:VCARD" in text.upper():
        try:
            return parse_vcard(text)
        except ValueError as exc:
            raise ImportResolveError("IMPORT_FAILED", "vCard 格式無法解析") from exc
    raise ImportResolveError("IMPORT_FAILED", "無法解析此 QR 內容，請改貼連結")


async def resolve_url_input(url: str) -> dict:
    text = url.strip()
    if not text:
        raise ImportResolveError("IMPORT_FAILED", "請輸入連結")
    if "BEGIN:VCARD" in text.upper():
        try:
            return parse_vcard(text)
        except ValueError as exc:
            raise ImportResolveError("IMPORT_FAILED", "vCard 格式無法解析") from exc
    if not text.startswith(("http://", "https://")):
        text = f"https://{text}"
    return await fetch_url(text)
