from collections import Counter

from app.modules.m5_search.sample_queries import _build_queries, _short_company_name


def test_short_company_name_aws():
    assert _short_company_name("Amazon Web Services Taiwan Ltd.") == "AWS"


def test_build_queries_product_and_label():
    queries = _build_queries(
        products=Counter({"工業電腦": 2}),
        labels=Counter({"Computex 2026": 3}),
        companies=Counter(),
    )
    assert len(queries) <= 3
    assert any("工業電腦" in q for q in queries)
    assert any("Computex 2026" in q for q in queries)


def test_build_queries_company_cluster():
    queries = _build_queries(
        products=Counter(),
        labels=Counter(),
        companies=Counter({"Amazon Web Services Taiwan Ltd.": 2, "Other Co": 1}),
    )
    assert any("AWS" in q for q in queries)
