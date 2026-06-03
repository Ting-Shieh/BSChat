import pytest

from app.modules.m2_capture.structured_html import parse_json_ld_contact


def test_parse_json_ld_person():
    html = """
    <script type="application/ld+json">
    {
      "@type": "Person",
      "name": "王小明",
      "jobTitle": "業務經理",
      "email": "ming@example.com",
      "telephone": "+886-912-345-678",
      "worksFor": {"@type": "Organization", "name": "Example Corp"},
      "image": "https://cdn.example.com/ming.jpg"
    }
    </script>
    """
    result = parse_json_ld_contact(html)
    assert result is not None
    assert result["fields"]["name"] == "王小明"
    assert result["fields"]["company"] == "Example Corp"
    assert result["resolver_type"] == "json_ld"
    assert result["image_url"].endswith("ming.jpg")


def test_parse_json_ld_missing_returns_none():
    assert parse_json_ld_contact("<html><body>no schema</body></html>") is None
