from app.modules.m2_capture.structured_html import extract_link_hints
from app.modules.m2_capture.import_normalize import normalize_import_fields

SPIDERCARD_SNIPPET = """
<a href="mailto:boxun_shao@adata.com">email</a>
<a href="https://www.adata.com/en/">Official Website</a>
<a href="https://www.google.com/maps/?q=內湖總部 : \r\n台北市內湖區潭美街533號25樓\r\n中和總部 : \r\n新北市中和區連城路258號18樓">map</a>
"""


def test_extract_link_hints_from_spidercard_html():
    hints = extract_link_hints(SPIDERCARD_SNIPPET)
    assert hints["websites"] == ["https://www.adata.com/en"]
    assert "台北市內湖區潭美街533號25樓" in hints["addresses"][0]


def test_normalize_fills_website_from_href_when_llm_missing():
    fields = {
        "name": "邵柏勛",
        "company": "威剛科技股份有限公司",
        "title": "工程師",
        "phones": [],
        "emails": [],
        "address": None,
        "website": None,
    }
    normalized = normalize_import_fields(
        fields,
        html_text=SPIDERCARD_SNIPPET,
        page_url="https://www.spidercard.com/web/company/info?cardId=x",
    )
    assert normalized["address"] == "台北市內湖區潭美街533號25樓"
    assert normalized["website"] == "https://www.adata.com/en"
