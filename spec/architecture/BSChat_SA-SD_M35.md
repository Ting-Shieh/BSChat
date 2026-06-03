# BSChat SA/SD — Module 3.5：個人公開資料補充（LinkedIn + LLM）

> **依據**：`BSChat_PM_M35.md`、DDR-74/75/76、M3/M1/M5 契約  
> **架構模式**：Modular Monolith + 背景 worker（同 M6 enrich）

---

## 1. 架構概覽

```
┌─────────────────────────────────────────────────────────────────┐
│  M1 Entitlement Gate（API + Worker 雙檢查）                        │
│  person_enrich_mode != linkedin_llm → 403 / skip job             │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│  Person Enrich Worker (M3.5)                                     │
│  1. Resolve input (url | search)                                 │
│  2. People API / Tavily extract → raw profile snippet           │
│  3. match_score                                                  │
│  4. LLM summarize (Gemini / Claude) → scope + confidence          │
│  5. Gate → write person_enrichments + contacts fields            │
│  6. enqueue contacts.index                                       │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│  PostgreSQL                                                      │
│  person_enrichments | person_enrich_jobs                         │
│  contacts (+ person_* / linkedin_url)                            │
└─────────────────────────────────────────────────────────────────┘
```

**事件触发**：

| 触发 | Event / Task |
|------|----------------|
| Contact upsert + linkedin_url | `person.enrich` `{ contact_id, trigger: "url_auto" }` |
| POST person-enrich | `person.enrich` `{ contact_id, trigger: "manual" }` |
| M5 深入查此人 | 同上 `trigger: "from_search"` |

---

## 2. 資料庫設計

### 2.1 `person_enrichments`（append-only）

```sql
CREATE TABLE person_enrichments (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id          UUID NOT NULL REFERENCES contacts(id),
  user_id             UUID NOT NULL,
  enrich_version      INT NOT NULL DEFAULT 1,
  trigger_type        VARCHAR(20) NOT NULL,  -- url_auto | manual | from_search
  source_type         VARCHAR(20) NOT NULL,  -- linkedin_url | people_api | web_search
  linkedin_url        TEXT,
  profile_headline    TEXT,
  profile_summary     TEXT,                  -- raw snippet / About 前 N 字
  person_scope        TEXT,                  -- LLM 输出「可能負責…」
  confidence          FLOAT NOT NULL,
  match_score         FLOAT NOT NULL,
  match_inputs        JSONB,                   -- { name_sim, company_sim, title_sim }
  model               VARCHAR(50),
  prompt_version      VARCHAR(20),
  status              VARCHAR(20) NOT NULL,  -- active | superseded | rejected | pending_confirm
  created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_person_enrich_contact_active
  ON person_enrichments(contact_id) WHERE status = 'active';
```

### 2.2 `person_enrich_jobs`

```sql
CREATE TABLE person_enrich_jobs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id      UUID NOT NULL,
  user_id         UUID NOT NULL,
  trigger_type    VARCHAR(20) NOT NULL,
  status          VARCHAR(20) NOT NULL,  -- queued | running | completed | failed | needs_confirmation
  error_code      VARCHAR(50),
  candidates      JSONB,                 -- [{ linkedin_url, headline, match_score }]
  idempotency_key VARCHAR(128) UNIQUE,
  started_at      TIMESTAMPTZ,
  completed_at    TIMESTAMPTZ,
  latency_ms      INT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.3 `contacts` 擴展欄位

```sql
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS linkedin_url TEXT;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS person_scope TEXT;           -- M3.5 主显示（gate 通过后）
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS person_scope_confidence FLOAT;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS person_enrich_status VARCHAR(20);  -- never | pending | completed | rejected
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS person_enriched_at TIMESTAMPTZ;
```

**与 M3 字段关系**：

| 字段 | Owner | 说明 |
|------|-------|------|
| `responsibility_scope` | M3 LLM | Free + Pro 均有；M3 pass 1/2 |
| `person_scope` | M3.5 | 仅 Pro；LinkedIn + LLM；详情优先显示 |
| `title` | OCR | 永不覆写 |

**search_text 拼接**（index worker）：

```
… | responsibility_scope | person_scope | …
```

M5 硬条件：引用 `person_scope` 时须 `person_scope_confidence ≥ 0.75` 且对应 enrichment `match_score ≥ 0.8`。

### 2.4 `user_entitlements` 擴展

```sql
ALTER TABLE user_entitlements ADD COLUMN IF NOT EXISTS person_enrich_mode VARCHAR(20) DEFAULT 'inference_only';
ALTER TABLE user_entitlements ADD COLUMN IF NOT EXISTS person_linkedin_quota_monthly INT DEFAULT 0;
ALTER TABLE user_entitlements ADD COLUMN IF NOT EXISTS person_linkedin_used_this_month INT DEFAULT 0;
ALTER TABLE user_entitlements ADD COLUMN IF NOT EXISTS person_linkedin_reset_at TIMESTAMPTZ;
ALTER TABLE user_entitlements ADD COLUMN IF NOT EXISTS person_linkedin_auto_on_url BOOLEAN DEFAULT FALSE;
```

**默认值**：

| plan | person_enrich_mode | quota | auto_on_url |
|------|-------------------|-------|-------------|
| free | inference_only | 0 | false |
| pro | linkedin_llm | 20 | true |
| enterprise（Enterprise Personal） | linkedin_llm | 100 ※ | true |

※ Quota 見 PRD §11.2.2 · **TBD**

---

## 3. API 規格

**Base**：`/api/v1` · Bearer JWT

### POST `/contacts/{contact_id}/person-enrich`

**Auth**：Pro / Enterprise only

**Request**：

```json
{
  "confirm_candidate_index": null
}
```

消歧后：

```json
{
  "confirm_candidate_index": 0
}
```

**Response 202**（queued）：

```json
{
  "job_id": "uuid",
  "status": "queued",
  "quota_remaining": 19
}
```

**Response 200**（needs_confirmation）：

```json
{
  "status": "needs_confirmation",
  "candidates": [
    {
      "index": 0,
      "linkedin_url": "https://linkedin.com/in/...",
      "headline": "OEM Sales Manager at ABC Tech",
      "match_score": 0.87
    }
  ]
}
```

**Errors**：

| Code | HTTP | 说明 |
|------|------|------|
| `PERSON_ENRICH_NOT_ALLOWED` | 403 | Free tier |
| `PERSON_LINKEDIN_QUOTA_EXCEEDED` | 429 | 月度用尽 |
| `PERSON_ENRICH_IN_PROGRESS` | 409 | 已有 running job |

### GET `/contacts/{contact_id}/person-enrich/status`

```json
{
  "status": "completed",
  "person_scope": "可能負責工業級 SSD OEM 通路",
  "confidence": 0.82,
  "match_score": 0.91,
  "source_type": "linkedin_url",
  "updated_at": "2026-05-20T10:00:00Z",
  "provenance_label": "LinkedIn 公開資料 · AI 整理 · 82%"
}
```

### POST `/contacts/{contact_id}/person-enrich/confirm`

Body: `{ "candidate_index": 0 }` → 继续 LLM + write

### POST `/contacts/{contact_id}/person-enrich/reject`

→ `person_enrichments.status=rejected`；clear `person_scope`；re-index

---

## 4. Worker：`person.enrich`

```python
async def run_person_enrich(payload: dict) -> None:
    user = await load_user(payload["user_id"])
    if user.entitlement.person_enrich_mode != "linkedin_llm":
        return  # silent skip for defense in depth

    contact = await load_contact(payload["contact_id"])

    if payload["trigger"] == "url_auto":
        raw = await fetch_by_url(contact.linkedin_url)
        match_score = 1.0
    else:
        candidates = await search_people(contact)
        if len(candidates) == 0:
            await finish_failed("NO_CANDIDATES")
            return
        if len(candidates) > 1 and not payload.get("confirm_candidate_index"):
            await save_needs_confirmation(candidates)
            return
        raw = candidates[payload.get("confirm_candidate_index", 0)]
        match_score = raw.match_score

    if match_score < 0.8:
        await save_needs_confirmation([raw])  # unless user confirmed
        return

    result = await llm_summarize_person_scope(raw, contact)
    if result.confidence < 0.75:
        await finish_partial(result)
        return

    await write_person_enrichment(contact, result, match_score)
    enqueue_contact_index(contact.id)
```

**Idempotency key**：`person:{contact_id}:{trigger}:{hour_bucket}`（manual 除外用 UUID）

**Quota**：manual / from_search 在 job **成功 gate 后**扣减；failed 不扣（R-35.9 Pilot 可调）

---

## 5. LLM Pipeline

**文件**：`backend/app/ai/pipelines/person_scope.py`

**Input**：

```json
{
  "display_name": "王小明",
  "company_name": "ABC Tech",
  "title": "OEM 業務經理",
  "profile_headline": "...",
  "profile_summary": "...",
  "company_products": ["工業電腦", "..."]
}
```

**Output schema**：

```json
{
  "person_scope": "可能負責 OEM 通路與 SI 伙伴经营",
  "confidence": 0.82
}
```

**Rules**（system prompt）：

- 繁体中文；1–2 句；以「可能负责…」开头
- 不得断言在职状态；不得编造客户名
- 不得仅重复 `title` 或 `profile_headline`
- 信息不足 → confidence < 0.75

---

## 6. 詳情 Response 擴展（DDR-27）

`GET /contacts/:id` → `sections.ai_inferred`：

```json
{
  "ai_inferred": {
    "responsibility_scope": {
      "value": "可能負責 …",
      "confidence": 0.67,
      "source": "ai_inferred",
      "pass": 2
    },
    "person_scope": {
      "value": "可能負責 …",
      "confidence": 0.82,
      "source": "linkedin",
      "match_score": 0.91,
      "linkedin_url": "https://…",
      "updated_at": "…"
    },
    "upgrade_cta": null
  }
}
```

**Free**：

```json
{
  "ai_inferred": {
    "responsibility_scope": { "…" },
    "person_scope": null,
    "upgrade_cta": {
      "feature": "linkedin_person_enrich",
      "label": "Pro：以 LinkedIn 公開資料核對職責"
    }
  }
}
```

---

## 7. Coupling Map

| From | To | Contract |
|------|-----|----------|
| M1 | M3.5 | `person_enrich_mode`, quota fields |
| M2 | M3.5 | `linkedin_url` on handoff |
| M3 | M3.5 | 并行；M3.5 不阻塞 M3 inference |
| M3.5 | M3 index | `person_scope` in search_text |
| M6 | M3.5 | 只读 `main_products` 作 LLM 输入；M6 不抓 LinkedIn |
| M5 | M3.5 | `from_search` trigger；match_reason 读 person 字段 |
| M3.5 | M1 | increment `person_linkedin_used_this_month` |

---

## 8. Failure Modes

| 失败 | 处理 | UX |
|------|------|-----|
| Free 误触发 | API 403 / worker skip | 升級 CTA |
| Quota 用尽 | 429 | 「本月 LinkedIn 補充已用完」 |
| No candidates | job failed | 「找不到公開 LinkedIn 資料」 |
| match 低 | needs_confirmation | 候选列表 |
| LLM 失败 | retry 2x → 留空 | 仍显示 M3 推估 |
| People API down | failed + alert | 稍后再试 |

---

## 9. 合规备忘

- 仅处理**用户自己收录**的联系人；workspace 隔离
- UI 必显数据来源与「可能不是同一人」提示（多候选时）
- 第三方 API 数据保留期限遵循供应商 DPA
- Enterprise 客户需独立告知书（台湾个资法目的限定）
- **禁止**存储 LinkedIn 密码 / cookie / 非公开字段

---

## 10. DDR 新增（架构层）

| ID | 决策 |
|----|------|
| DDR-74 | Free=M3 LLM only；Pro+=M3.5 |
| DDR-75 | 不全库 silent 搜人；match<0.8 不写入 |
| DDR-76 | 不覆写 OCR title；person 与 M3 字段并存 |

---

*SA/SD M3.5 v1.0 — SDLC Phase 1*
