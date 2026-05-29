import re
import unicodedata

_SUFFIXES = (
    "股份有限公司",
    "有限公司",
    "公司",
    "co., ltd.",
    "co.,ltd.",
    "co ltd",
    "inc.",
    "inc",
    "corp.",
    "corp",
    "ltd.",
    "ltd",
    "llc",
)


def normalize_company_name(name: str) -> str:
    text = unicodedata.normalize("NFKC", name.strip().lower())
    for suffix in _SUFFIXES:
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "", text)
    return text or name.strip().lower()
