import pytest

from app.modules.m2_capture.vcard_parser import parse_vcard


SAMPLE_VCARD = """BEGIN:VCARD
VERSION:3.0
FN:游瑞恩
ORG:瓏山林度假飯店
TITLE:業務經理
TEL;TYPE=CELL:0912345678
EMAIL:ray@example.com
URL:https://hotel.example.com
END:VCARD
"""


def test_parse_vcard_maps_fields():
    result = parse_vcard(SAMPLE_VCARD)
    fields = result["fields"]
    assert fields["name"] == "游瑞恩"
    assert fields["company"] == "瓏山林度假飯店"
    assert fields["title"] == "業務經理"
    assert "0912345678" in fields["phones"][0]
    assert fields["emails"][0] == "ray@example.com"
    assert result["resolver_type"] == "vcard_text"
    assert result["field_confidences"]["name"] >= 0.9


def test_parse_vcard_rejects_empty():
    with pytest.raises(ValueError):
        parse_vcard("BEGIN:VCARD\nVERSION:3.0\nEND:VCARD")


def test_parse_vcard_unfolds_lines():
    folded = """BEGIN:VCARD
VERSION:3.0
FN:王
 小明
ORG:台灣亞馬遜網路服務有限公司
END:VCARD"""
    result = parse_vcard(folded)
    assert "王" in (result["fields"]["name"] or "")
