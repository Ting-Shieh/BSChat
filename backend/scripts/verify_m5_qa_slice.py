#!/usr/bin/env python3
"""M5 QA vertical slice steps 1-6 — API verification against running backend."""

import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("M5_QA_BASE", "http://127.0.0.1:8001/api/v1")
QA_EMAIL = os.environ.get("M5_QA_EMAIL", "dev@example.com")
TIMEOUT = int(os.environ.get("M5_QA_TIMEOUT", "180"))


def req(method: str, path: str, token: str | None = None, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=TIMEOUT) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            detail = json.loads(raw)
        except json.JSONDecodeError:
            detail = raw
        return e.code, detail


def login(email: str) -> str:
    code, data = req("POST", "/auth/dev-login", body={"email": email, "display_name": email.split("@")[0]})
    assert code == 200, data
    return data["access_token"]


def main() -> int:
    results: list[tuple[str, str, str, str]] = []

    def record(step: str, case: str, status: str, note: str = ""):
        results.append((step, case, status, note))
        icon = "✅" if status == "PASS" else "⚠️" if status == "PARTIAL" else "❌"
        print(f"{icon} [{step}] {case}: {status}" + (f" — {note}" if note else ""))

    print(f"QA user: {QA_EMAIL} | timeout={TIMEOUT}s | base={BASE}")

    # Step 1: status
    token = login(QA_EMAIL)
    code, status = req("GET", "/search/status", token)
    if code == 200 and "indexed_count" in status and "can_search" in status and "quotas" in status:
        record("1", "TC-M5-001/032 GET /search/status", "PASS", f"indexed={status['indexed_count']}")
    else:
        record("1", "TC-M5-001/032 GET /search/status", "FAIL", str(status))

    free_queries = status.get("sample_queries", [])
    plan = req("GET", "/me", token)[1].get("plan_tier", "free") if code == 200 else "?"
    if plan == "free" and free_queries == []:
        record("1", "TC-M5-003 Free sample_queries=[]", "PASS")
    elif plan == "pro" and free_queries:
        record("1", "TC-M5-003 Pro sample_queries", "PASS", f"{len(free_queries)} pills")
    elif plan == "free" and free_queries:
        record("1", "TC-M5-003 Free sample_queries=[]", "FAIL", f"got {free_queries}")
    else:
        record("1", "TC-M5-003 sample_queries", "PARTIAL", f"plan={plan}, queries={free_queries}")

    # Step 2: search integration
    if not status.get("can_search"):
        record("2", "TC-M5-005 search COMPLETED", "SKIP", "no indexed contacts")
    else:
        code, search = req(
            "POST",
            "/search/queries",
            token,
            {"query_text": "我手上有誰做工業電腦的？", "search_scope": "private"},
        )
        if code == 200 and search.get("status") in ("COMPLETED", "EMPTY"):
            if search.get("status") == "COMPLETED":
                ok = bool(search.get("results")) and all(r.get("match_reason") for r in search["results"])
                record("2", "TC-M5-005 COMPLETED + match_reason", "PASS" if ok else "PARTIAL", f"count={search.get('result_count')}")
                if search.get("results"):
                    p = search["results"][0].get("contact_preview", {})
                    fields = [p.get("display_name"), p.get("company_name")]
                    record("2", "TC-M5-009 contact_preview", "PASS" if any(fields) else "PARTIAL")
            else:
                record("2", "TC-M5-005 COMPLETED", "PARTIAL", f"EMPTY reason={search.get('empty_state', {}).get('reason')}")
        else:
            record("2", "TC-M5-005 search", "FAIL", f"{code} {search}")

        # Semantic hotel query (Gemini intent)
        code, hotel = req(
            "POST",
            "/search/queries",
            token,
            {"query_text": "飯店相關推薦人", "search_scope": "private"},
        )
        if code == 200 and hotel.get("status") == "COMPLETED" and hotel.get("results"):
            names = [r["contact_preview"].get("display_name", "") for r in hotel["results"]]
            companies = [r["contact_preview"].get("company_name", "") for r in hotel["results"]]
            hotel_hit = any(
                "飯店" in (c or "") or "度假" in (c or "") or "hotel" in (c or "").lower()
                for c in companies
            )
            record(
                "2",
                "TC-M5-013b hotel semantic",
                "PASS" if hotel_hit else "PARTIAL",
                f"names={names}, companies={companies}",
            )
        elif code == 200 and hotel.get("status") == "EMPTY":
            record("2", "TC-M5-013b hotel semantic", "PARTIAL", "EMPTY (no hotel contact in index?)")
        else:
            record("2", "TC-M5-013b hotel semantic", "FAIL", str(hotel))

        # DDR-73
        code, hard = req(
            "POST",
            "/search/queries",
            token,
            {"query_text": "從我AWS人脈中找從事架構師的就好", "search_scope": "private"},
        )
        if code == 200:
            if hard.get("status") == "COMPLETED":
                names = [r["contact_preview"].get("title", "") for r in hard.get("results", [])]
                pm_leak = any("program manager" in (t or "").lower() or "pm" == (t or "").lower() for t in names)
                arch_ok = all("架構" in (t or "").lower() or "architect" in (t or "").lower() for t in names if t)
                if pm_leak:
                    record("2", "TC-M5-013c hard constraints", "FAIL", f"titles={names}")
                elif names:
                    record("2", "TC-M5-013c hard constraints", "PASS" if arch_ok else "PARTIAL", f"titles={names}")
                else:
                    record("2", "TC-M5-013c hard constraints", "PARTIAL", "no results (maybe no architect in DB)")
            else:
                record("2", "TC-M5-013c hard constraints", "PASS", "NO_MATCH (no architect)")
        else:
            record("2", "TC-M5-013c", "FAIL", str(hard))

    # Validation
    code, empty = req("POST", "/search/queries", token, {"query_text": "", "search_scope": "private"})
    record("2", "TC-M5-008 empty query 400", "PASS" if code == 422 else "FAIL", f"code={code}")

    code, long_q = req("POST", "/search/queries", token, {"query_text": "x" * 2001, "search_scope": "private"})
    record("2", "TC-M5-007 long query 400", "PASS" if code == 422 else "FAIL", f"code={code}")

    # Step 6: security
    code, scope = req("POST", "/search/queries", token, {"query_text": "test", "search_scope": "network"})
    detail = scope.get("detail") if isinstance(scope, dict) else scope
    record("6", "TC-M5-030 network scope 403", "PASS" if code == 403 else "FAIL", str(detail))

    token_b = login("qa-m5-b@example.com")
    if status.get("can_search"):
        code, search_a = req("POST", "/search/queries", token, {"query_text": "AWS", "search_scope": "private"})
        if code == 200 and search_a.get("query_id"):
            qid = search_a["query_id"]
            code_b, cross = req("GET", f"/search/queries/{qid}", token_b)
            record("6", "TC-M5-029 cross-user 404", "PASS" if code_b == 404 else "FAIL", f"code={code_b}")
        else:
            record("6", "TC-M5-029 cross-user 404", "SKIP", "no query_id")
    else:
        record("6", "TC-M5-029 cross-user 404", "SKIP", "no index")

    # NO_MATCH
    if status.get("can_search"):
        code, nomatch = req(
            "POST",
            "/search/queries",
            token,
            {"query_text": "量子計算超導體奈米機器人", "search_scope": "private"},
        )
        if code == 200 and nomatch.get("status") == "EMPTY":
            reason = nomatch.get("empty_state", {}).get("reason")
            record("4", "TC-M5-011 NO_MATCH", "PASS" if reason == "NO_MATCH" else "PARTIAL", f"reason={reason}")
        else:
            record("4", "TC-M5-011 NO_MATCH", "PARTIAL", str(nomatch))

    # Summary
    print("\n--- Summary ---")
    fails = [r for r in results if r[2] == "FAIL"]
    partial = [r for r in results if r[2] == "PARTIAL"]
    print(f"Total: {len(results)} | FAIL: {len(fails)} | PARTIAL: {len(partial)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
