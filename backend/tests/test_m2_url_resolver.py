import pytest

from app.modules.m2_capture.url_resolver import ImportResolveError, _validate_public_url, resolve_qr_payload


def test_validate_public_url_rejects_localhost():
    with pytest.raises(ImportResolveError) as exc:
        _validate_public_url("http://127.0.0.1/test")
    assert exc.value.code == "UNSUPPORTED_URL"


def test_validate_public_url_rejects_metadata_ip():
    with pytest.raises(ImportResolveError):
        _validate_public_url("http://169.254.169.254/latest/meta-data/")


def test_resolve_qr_vcard_payload():
    payload = """BEGIN:VCARD
VERSION:3.0
FN:測試使用者
ORG:測試公司
TITLE:PM
EMAIL:test@example.com
END:VCARD"""
    result = resolve_qr_payload(payload)
    assert result["fields"]["name"] == "測試使用者"
    assert result["fields"]["company"] == "測試公司"


def test_resolve_qr_empty_fails():
    with pytest.raises(ImportResolveError) as exc:
        resolve_qr_payload("   ")
    assert exc.value.code == "IMPORT_FAILED"
