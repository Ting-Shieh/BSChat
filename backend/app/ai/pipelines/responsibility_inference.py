"""M3 responsibility scope inference (Pass 1 / Pass 2)."""

import json
import re
import time

import httpx

from app.ai.gemini_client import gemini_generate_text
from app.ai.schemas.responsibility_output import ResponsibilityOutput
from app.core.config import get_settings

settings = get_settings()

PROMPT_VERSION = "v1"

PASS1_PROMPT = """你是 B2B 人脈助手。根據職稱與公司名稱，推測此人在該公司「可能負責的業務範圍」。

職稱：{title}
公司：{company_name}

規則：
- 輸出 JSON only：{{ "scope": "...", "confidence": 0.0-1.0 }}
- scope 使用繁體中文，1-2 句，必須以「可能負責」開頭
- 不要只重複職稱字面；不要臆測具體客戶名；不要寫在職狀態
- 職稱過於泛化（如「經理」「Manager」）且公司資訊不足時，confidence 必須 < 0.6
"""

PASS2_PROMPT = """你是 B2B 人脈助手。根據職稱、公司與已知主要產品，推測此人「可能負責的業務範圍」。

職稱：{title}
公司：{company_name}
公司主要產品/服務：{products}

規則：
- 輸出 JSON only：{{ "scope": "...", "confidence": 0.0-1.0 }}
- scope 使用繁體中文，1-2 句，必須以「可能負責」開頭
- 結合產品線推論職責；不要只重複職稱或產品列表
- 資訊不足時 confidence 必須 < 0.6
"""


def _parse_json(text: str) -> ResponsibilityOutput:
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    parsed = json.loads(text.strip())
    scope = str(parsed.get("scope", "")).strip()
    if scope and not scope.startswith("可能負責"):
        scope = f"可能負責{scope.lstrip('可能负责').lstrip('可能負責')}"
    return ResponsibilityOutput(scope=scope, confidence=float(parsed.get("confidence", 0.0)))


def _mock_inference(
    title: str,
    company_name: str | None,
    company_products: list[str] | None,
    pass_number: int,
) -> ResponsibilityOutput:
    title_text = title or ""
    lower = title_text.lower()
    products = company_products or []
    products_text = " ".join(products)

    if "oem" in lower or "OEM" in title_text:
        return ResponsibilityOutput(
            scope="可能負責 OEM 通路與大客戶開發",
            confidence=0.72,
        )
    if "fae" in lower or "FAE" in title_text or "應用工程" in title_text:
        return ResponsibilityOutput(
            scope="可能負責技術支援與客戶導入方案",
            confidence=0.7,
        )
    if pass_number == 2 and products:
        if any(k in products_text for k in ("工業", "嵌入式", "SSD", "儲存")):
            return ResponsibilityOutput(
                scope="可能負責工業級產品之專案與通路業務",
                confidence=0.68,
            )
        return ResponsibilityOutput(
            scope=f"可能負責與{'、'.join(products[:2])}相關的業務推廣",
            confidence=0.65,
        )
    if company_name and len(title_text.strip()) >= 4:
        return ResponsibilityOutput(
            scope=f"可能負責{company_name}相關業務推廣與客戶經營",
            confidence=0.62,
        )
    generic = re.match(r"^(經理|主管|Manager|Director)$", title_text.strip(), re.I)
    if generic or len(title_text.strip()) < 3:
        return ResponsibilityOutput(scope="可能負責一般業務", confidence=0.45)
    return ResponsibilityOutput(
        scope=f"可能負責與{title_text}相關的業務範圍",
        confidence=0.55,
    )


def scope_title_similarity(scope: str, title: str) -> float:
    """Rough overlap 0-1; high means scope mostly repeats title."""
    if not scope or not title:
        return 0.0
    a = re.sub(r"^可能負責", "", scope).strip().lower()
    b = title.strip().lower()
    if not a or not b:
        return 0.0
    if a == b or a in b or b in a:
        return 1.0
    a_tokens = set(re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]+", a))
    b_tokens = set(re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]+", b))
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / max(len(a_tokens), len(b_tokens))


async def infer_responsibility(
    *,
    title: str,
    company_name: str | None,
    company_products: list[str] | None = None,
    pass_number: int = 1,
) -> tuple[ResponsibilityOutput, str, str]:
    """Returns (output, model, prompt_version)."""
    use_mock = settings.inference_use_mock
    if not use_mock and settings.effective_inference_provider == "mock":
        use_mock = True

    if use_mock:
        return _mock_inference(title, company_name, company_products, pass_number), "mock", PROMPT_VERSION

    products_str = "、".join(company_products or []) or "（未知）"
    company_str = company_name or "（未知）"
    if pass_number >= 2:
        prompt = PASS2_PROMPT.format(
            title=title,
            company_name=company_str,
            products=products_str,
        )
    else:
        prompt = PASS1_PROMPT.format(title=title, company_name=company_str)

    provider = settings.effective_inference_provider
    start = time.perf_counter()

    if provider == "gemini":
        text = await gemini_generate_text(prompt, model=settings.gemini_inference_model)
        output = _parse_json(text)
        return output, settings.gemini_inference_model, PROMPT_VERSION

    if provider == "claude" and settings.anthropic_api_key:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        msg = await client.messages.create(
            model=settings.inference_model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        output = _parse_json(msg.content[0].text)
        return output, settings.inference_model, PROMPT_VERSION

    return _mock_inference(title, company_name, company_products, pass_number), "mock", PROMPT_VERSION
