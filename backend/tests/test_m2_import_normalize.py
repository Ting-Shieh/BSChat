from app.modules.m2_capture.import_normalize import normalize_import_fields

MYSC_HTML = """
Please select a language below Traditional Chinese 賴昀君 Aply Lai
資深專案經理 Senior Project Manager 新創事業
威剛科技股份有限公司 ADATA Technology Co., Ltd.
mailto:aply_lai@adata.com
ADATA Technology is the world's second-largest manufacturer of DRAM memory
"""


def test_prefers_cjk_name_over_english():
    fields = {
        "name": "Aply Lai",
        "company": "Aply Lai",
        "title": "ADATA Technology is the world&#39;s second-largest manufacturer of DRAM",
        "phones": [],
        "emails": ["aply_lai@adata.com"],
        "address": None,
        "website": "https://mysc.cc/company/x",
    }
    out = normalize_import_fields(fields, html_text=MYSC_HTML, page_url="https://mysc.cc/company/x")
    assert out["name"] == "賴昀君"
    assert "manufacturer" not in (out["title"] or "").lower()
    assert "&#39;" not in (out["title"] or "")


def test_unescapes_html_entities():
    out = normalize_import_fields(
        {"name": "Test", "company": None, "title": "world&#39;s best", "phones": [], "emails": []},
        html_text="",
        page_url="",
    )
    assert out["title"] == "world's best"
