# BSChat SA/SD — Module 3.5：個人公開資料補充（LinkedIn + LLM）

> **依據**：`BSChat_PM_M35.md`、DDR-74/75/76、**DDR-81~85（2026-06-11 data_source 拍板）**、`spec/product/BSChat_M35_data_source.md`、M3/M1/M5 契約  
> **架構模式**：Modular Monolith；**manual / from_search 於 request 內同步執行**，**url_auto 走背景 worker**（與 M6 純背景 enrich 不同）  
> **版本**：v1.1（2026-06-11 對齊 data_source 6 類動態標籤；解除紅旗 1）

> ⚠️ **v1.0 → v1.1 修正重點**：原 v1.0 §3/§6 寫死 `provenance_label: "LinkedIn 公開資料 · AI 整理 · n%"` 與 `source: "linkedin"`，**已作廢**。來源一律以 `data_source`（6 類）動態決定標籤，禁止把 mock / 推論結果標為「LinkedIn 公開資料」。

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
  source_type         VARCHAR(20) NOT NULL,  -- linkedin_url | people_api | web_search | card_inference | user_manual
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
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS person_enrich_status VARCHAR(20);  -- never | pending | completed | insufficient | rejected
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS person_enriched_at TIMESTAMPTZ;
```

> **`insufficient`（v1.1 新增）**：信心低於門檻 或 有 URL 讀不到。此狀態 `person_scope` 為空、**不扣額度**，UI 顯示原因 + 導向 M3 推估（禁止 `completed` 但 `person_scope` 為空，舊資料以 `insufficient` 呈現）。

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

## 2.5 `data_source` 對外語意層（v1.1 · DDR-85）

`source_type` 是 DB 技術欄；對外（API `data_source` + UI `provenance_label`）**一律經此映射**，禁止寫死字串。

| `source_type`(DB) | 條件 | `data_source`(API) | `provenance_label`(UI) | 扣 LinkedIn 額度 |
|---|---|---|---|:--:|
| `linkedin_url` | 有 URL 且讀到真頁片段 | `linkedin_profile` | ✦ LinkedIn 個人頁 · AI 整理 · {n}% | 是 |
| `people_api`（有 URL） | 搜尋命中且回傳 URL | `linkedin_search` | ✦ LinkedIn 搜尋 · AI 整理 · {n}% | 是 |
| `people_api`（無 URL，legacy mock） | 舊 mock 資料 | `card_inference` | ○ 名片推估（未找到 LinkedIn）· AI 整理 · {n}% | 否 |
| `web_search` | 有 URL 但僅抓到公開網路摘要 | `linkedin_url_public` | ○ 依連結公開摘要 · AI 整理 · {n}% | 是（手動） |
| `card_inference` | 找不到，純名片推論 | `card_inference` | ○ 名片推估（未找到 LinkedIn）· AI 整理 · {n}% | 否 |
| `user_manual` | 使用者自填 | `user_manual` | ✎ 使用者筆記 | 否 |
| —（讀取失敗未 fallback） | 有 URL 讀不到 | `unavailable` | 空狀態 + 說明 | 否 |

**mock 防冒充紅線（紅旗 2）**：`person_search_provider=mock` 或無真實 snippet 時，**禁止**輸出 `linkedin_profile` / `linkedin_search`；只能 `card_inference` 或 `unavailable`，UI 不得出現 ✦ LinkedIn。實作可在 `card_inference` 標籤追加「（開發環境未接 LinkedIn API）」提示。

**confidence 門檻（依來源分級）**：

| 路徑 | gate（config） | 未達門檻 |
|---|---|---|
| `linkedin_profile` / `linkedin_search` | `person_confidence_gate` = 0.75 | `insufficient`，不扣額度 |
| `linkedin_url_public`（web_search on URL） | `person_confidence_gate_web` = 0.70 | 同上 |
| `card_inference` | `person_confidence_gate_card` = 0.65 | 同上 |

match 門檻：`person_match_gate` = 0.8（低於 → `needs_confirmation`，不寫入）。

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

**執行模式（v1.1 修正）**：manual / confirm / from_search **於 request 內同步執行**整條 pipeline，直接回 `200` 帶終態（`completed` / `needs_confirmation` / `insufficient` / `rejected`）。只有 `url_auto`（收錄後自動）走背景 worker。

**Response 200**（completed）：

```json
{
  "status": "completed",
  "person_scope": "可能負責工業級 SSD OEM 通路",
  "confidence": 0.82,
  "match_score": 0.91,
  "data_source": "linkedin_profile",
  "provenance_label": "✦ LinkedIn 個人頁 · AI 整理 · 82%",
  "quota_remaining": 19
}
```

**Response 200**（insufficient — 信心不足 / URL 讀不到）：

```json
{
  "status": "insufficient",
  "data_source": "card_inference",
  "message": "AI 整理信心 60% 低於門檻 65%，未寫入此區塊。",
  "quota_remaining": 20
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
  "data_source": "linkedin_profile",
  "provenance_label": "✦ LinkedIn 個人頁 · AI 整理 · 82%",
  "updated_at": "2026-05-20T10:00:00Z"
}
```

> `data_source` / `provenance_label` 一律由 §2.5 映射產生（`person_data_source()` / `person_provenance_label()`），**不得寫死**。

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

    if contact.linkedin_url:
        raw = await fetch_by_url(contact.linkedin_url)
        if raw is None:                       # DDR-83：有 URL 讀不到
            await finish_insufficient(data_source="unavailable")  # 不 fallback，不扣額度
            return
        match_score = raw.match_score
    else:
        candidates = await search_people(contact)
        if len(candidates) == 0:              # DDR-82：無 URL 搜不到 → 自動 card_inference
            raw = build_card_inference_candidate(contact)
            match_score = 1.0                 # skip match gate
        elif len(candidates) > 1 and not payload.get("confirm_candidate_index"):
            await save_needs_confirmation(candidates)
            return
        else:
            raw = candidates[payload.get("confirm_candidate_index", 0)]
            match_score = raw.match_score

    if raw.source_type != "card_inference" and match_score < person_match_gate:  # 0.8
        await save_needs_confirmation([raw])
        return

    result = await llm_summarize_person_scope(raw, contact)
    gate = confidence_gate_for(raw.source_type)  # 0.75 / 0.70 / 0.65（見 §2.5）
    if result.confidence < gate:
        await finish_insufficient(data_source=map(raw.source_type))  # 不扣額度
        return

    await write_person_enrichment(contact, result, match_score)  # 扣額度規則見下
    enqueue_contact_index(contact.id)
```

**Idempotency key**：`person:{contact_id}:{trigger}:{uuid}`；manual 15s 內重複點擊去抖、url_auto/from_search 24h 冪等略過。

**Quota（DDR-84）**：只有「成功寫入**且為 LinkedIn 路徑**」才扣 `person_linkedin`：
- `url_auto` → **永不扣**
- `card_inference` / `user_manual` / `unavailable` → **不扣**
- `linkedin_url` / `people_api`（有 URL）→ 扣；manual 且原本就有 URL 的 `web_search` → 扣

---

## 5. LLM Pipeline

**文件**：`backend/app/ai/pipelines/person_enrich.py`（候選解析 + `summarize_person_scope`）；輸出 schema `backend/app/ai/schemas/person_scope_output.py`；LinkedIn 抓取 `person_linkedin_web.py`

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
      "data_source": "linkedin_profile",
      "provenance_label": "✦ LinkedIn 個人頁 · AI 整理 · 82%",
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
| Free 误触发 | API 403 `PERSON_ENRICH_NOT_ALLOWED` / worker skip | 升級 CTA |
| Quota 用尽 | 429 `PERSON_LINKEDIN_QUOTA_EXCEEDED` | 「本月 LinkedIn 補充已用完」 |
| **無 URL 且搜尋 0 筆**（DDR-82） | 自動 `card_inference`（達 0.65 門檻才寫入） | ○ 名片推估（未找到 LinkedIn） |
| **有 URL 但讀不到**（DDR-83） | `insufficient` + `data_source=unavailable`，**不扣額度** | 「請確認連結是否正確，或改為自行輸入」 |
| 信心低於門檻 | `insufficient`（`person_scope` 空），**不扣額度** | 說明原因 + 導向 M3 推估 |
| match 低 | `needs_confirmation` | 候选列表 |
| mock / 無真實 snippet（紅旗 2） | 禁止標 LinkedIn；降為 `card_inference` 或 `unavailable` | 不得出现 ✦ LinkedIn |
| LLM 失败 | retry → `insufficient` | 仍显示 M3 推估 |

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
| **DDR-81** | M3.5 与 M3 **分区呈现**；M3 推估降为「系统参考（名片推估）」（builder 回 `has_m3_fallback`） |
| **DDR-82** | 失败混合 fallback：有 URL 读不到→停下问；无 URL 搜不到→自动 `card_inference` |
| **DDR-83** | 有 URL 读不到 → `data_source=unavailable` + `insufficient`，不扣额度 |
| **DDR-84** | `card_inference` 免费（不扣 LinkedIn / 不扣 M3） |
| **DDR-85** | `data_source` 6 类；对外标签经 §2.5 映射，禁止写死 |

---

## 11. v1.1 變更摘要（紅旗 1 對齊）

| 區段 | v1.0（作廢） | v1.1 |
|------|------|------|
| §3 / §6 標籤 | 寫死「LinkedIn 公開資料 · AI 整理 · n%」 | `data_source`(6 類) 動態映射（§2.5） |
| §3 執行 | 202 queued（worker） | manual/from_search 同步 200；僅 url_auto 走 worker |
| §4 無候選 | `NO_CANDIDATES` failed | 自動 `card_inference`（DDR-82） |
| 有 URL 讀不到 | 未定義 | `unavailable` + `insufficient`（DDR-83） |
| confidence gate | 單一 0.75 | 分級 0.75 / 0.70 / 0.65（§2.5） |
| 額度 | 成功即扣 | 僅 LinkedIn 路徑扣；card_inference/url_auto 不扣（DDR-84） |
| status enum | never/pending/completed/rejected | +`insufficient` |

> R-35.7（原「引用 person 欄位須標 LinkedIn 公開資料」）**作廢**，改依 §2.5 `data_source`。

---

*SA/SD M3.5 v1.1 — 2026-06-11 對齊 data_source（DDR-81~85）；v1.0 為 SDLC Phase 1 初版*
