"""M3 responsibility inference unit tests."""

import pytest

from app.ai.pipelines.responsibility_inference import (
    _mock_inference,
    infer_responsibility,
    scope_title_similarity,
)
from app.modules.m3_contacts.inference_service import CONFIDENCE_GATE


@pytest.mark.asyncio
async def test_mock_pass1_oem_title():
    out = _mock_inference("OEM 業務經理", "ABC Tech", None, 1)
    assert out.confidence >= CONFIDENCE_GATE
    assert out.scope.startswith("可能負責")
    assert "OEM" in out.scope or "通路" in out.scope


@pytest.mark.asyncio
async def test_mock_generic_title_low_confidence():
    out = _mock_inference("經理", None, None, 1)
    assert out.confidence < CONFIDENCE_GATE


@pytest.mark.asyncio
async def test_mock_pass2_with_products():
    out = _mock_inference(
        "業務經理",
        "威剛科技",
        ["工業級 SSD", "嵌入式模組"],
        2,
    )
    assert out.confidence >= CONFIDENCE_GATE
    assert "工業" in out.scope or "SSD" in out.scope or "嵌入式" in out.scope


@pytest.mark.asyncio
async def test_scope_title_similarity_penalty():
    sim = scope_title_similarity("OEM 業務經理", "OEM 業務經理")
    assert sim >= 0.85


@pytest.mark.asyncio
async def test_infer_responsibility_uses_mock_when_configured(monkeypatch):
    monkeypatch.setattr(
        "app.ai.pipelines.responsibility_inference.settings.inference_use_mock",
        True,
    )
    out, model, _ = await infer_responsibility(
        title="FAE",
        company_name="Chip Co",
        pass_number=1,
    )
    assert model == "mock"
    assert out.confidence >= CONFIDENCE_GATE
