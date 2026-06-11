"""vCard 3.0/4.0 text parser for digital business card import."""

import re
import unicodedata

_VCARD_BEGIN = re.compile(r"^BEGIN\s*:\s*VCARD", re.I | re.M)
_VCARD_END = re.compile(r"^END\s*:\s*VCARD", re.I | re.M)


def _unfold(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    for line in lines:
        if line.startswith((" ", "\t")) and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return "\n".join(out)


def _parse_properties(text: str) -> dict[str, list[str]]:
    props: dict[str, list[str]] = {}
    for line in _unfold(text).split("\n"):
        if ":" not in line or line.startswith("#"):
            continue
        key_part, _, value = line.partition(":")
        key = key_part.split(";", 1)[0].strip().upper()
        value = value.strip()
        if not key or not value:
            continue
        props.setdefault(key, []).append(value)
    return props


def _first(props: dict[str, list[str]], *keys: str) -> str | None:
    for key in keys:
        vals = props.get(key.upper())
        if vals and vals[0].strip():
            return vals[0].strip()
    return None


def _name_from_n(props: dict[str, list[str]]) -> str | None:
    raw = _first(props, "N")
    if not raw:
        return None
    parts = raw.split(";")
    family = parts[0].strip() if parts else ""
    given = parts[1].strip() if len(parts) > 1 else ""
    if given and family:
        return f"{family}{given}" if _looks_cjk(family + given) else f"{given} {family}".strip()
    return family or given or None


def _looks_cjk(text: str) -> bool:
    for ch in text:
        if unicodedata.name(ch, "").startswith("CJK"):
            return True
    return False


def _normalize_phone(raw: str) -> str:
    return re.sub(r"[^\d+]", "", raw)


def _pick_linkedin_url(props: dict[str, list[str]]) -> str | None:
    for raw in props.get("URL", []):
        url = raw.strip()
        if "linkedin.com/in/" in url.lower():
            return url
    return None


def parse_vcard(text: str) -> dict:
    """Parse vCard text into BSChat extracted_fields + confidences."""
    if not _VCARD_BEGIN.search(text):
        raise ValueError("NOT_VCARD")

    block = text
    match_begin = _VCARD_BEGIN.search(text)
    match_end = _VCARD_END.search(text)
    if match_begin and match_end:
        block = text[match_begin.start() : match_end.end()]

    props = _parse_properties(block)
    name = _first(props, "FN") or _name_from_n(props)
    company = _first(props, "ORG")
    title = _first(props, "TITLE")
    phones = [_normalize_phone(v) for v in props.get("TEL", []) if _normalize_phone(v)]
    emails = [v.lower() for v in props.get("EMAIL", []) if "@" in v]
    address = _first(props, "ADR")
    if address:
        address = ";".join(p for p in address.split(";") if p.strip()).replace(";;", " ").strip() or address
    website = _first(props, "URL")
    linkedin_url = _pick_linkedin_url(props)

    fields = {
        "name": name,
        "company": company,
        "title": title,
        "phones": phones[:3],
        "emails": emails[:3],
        "address": address,
        "website": website,
        "linkedin_url": linkedin_url,
    }
    confidences: dict[str, float] = {}
    for key in ("name", "company", "title", "address", "website"):
        if fields.get(key):
            confidences[key] = 0.95
    if phones:
        confidences["phones"] = 0.95
    if emails:
        confidences["emails"] = 0.95

    if not name and not company and not phones and not emails:
        raise ValueError("EMPTY_VCARD")

    return {
        "fields": fields,
        "field_confidences": confidences,
        "raw_text": block.strip(),
        "resolver_type": "vcard_text",
    }
