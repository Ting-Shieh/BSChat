# BSChat PM L3 — Module 3.5：個人公開資料補充（LinkedIn + LLM）

> **版本**：v1.0（2026-05-20）  
> **狀態**：PM L3 ✅ 可鎖定（待 Pilot 驗證 API 供應商與 quota）  
> **依據**：`BSChat_PRD_v2.md` §11.2、§12.5、DDR-74/75/76；M3 職責推估、M1 訂閱、M5/M6 邊界

---

## 模組定位

> M3.5 是 **Pro / Enterprise 專屬** 的「個人職場公開資料 → 結構化職責摘要」層。  
> **Free 使用者永不觸發**本模組；Free 的個人職責理解 **僅由 M3 LLM 推估** 提供（DDR-74）。

**與 M3 的關係**：

```
                    Free                          Pro / Enterprise
                      │                                    │
M2 Handoff ──→ M3 LLM Pass 1/2 ──→ responsibility_scope   （所有人）
                      │                                    │
                      │                    M3.5 LinkedIn + LLM（僅付費）
                      │                              │
                      └──────────→ 詳情 ai_inferred 區（分 source 顯示）
                                      │
                                      └──→ M5 index（person 欄位受 gate 限制）
```

**不做**：
- ❌ Free 或 silent 對全名片庫批量搜 LinkedIn
- ❌ 人員在職 / 離職追蹤（DDR-33）
- ❌ 覆寫 OCR `title` 或 M6 公司產品
- ❌ 自建 LinkedIn 爬蟲 / 假帳號
- ❌ 跨使用者搜尋他人私人聯絡人（僅 enrich **自己 workspace** 內 Contact）

---

## L3.1 — Sub-features

| # | Sub-feature | 優先 | 方案 | 驗收標準 |
|---|-------------|------|------|---------|
| F-35.1 | **M1 Entitlement Gate** | **P0** | 全部 | Free 呼叫 API → 403 `PERSON_ENRICH_NOT_ALLOWED` |
| F-35.2 | **LinkedIn URL 自動補充** | **P0** | Pro | import/OCR 含 `linkedin.com/in/…` → 背景 job；不占 manual quota（或 Pilot 後定） |
| F-35.3 | **手動「LinkedIn 補充」** | **P0** | Pro | 詳情按鈕；扣 `person_linkedin_quota_monthly` |
| F-35.4 | **People Search + Match** | **P0** | Pro | name+company+title → 0~N 候選；`match_score` |
| F-35.5 | **LLM 摘要職責** | **P0** | Pro | 從 headline/現職/About 片段 → `person_scope` + confidence |
| F-35.6 | **Match / Confidence Gate** | **P0** | 全部 | score<0.8 或 conf<0.75 → 不寫入；僅 UI 候選 |
| F-35.7 | **Pro 失敗 Fallback** | **P0** | Pro | M3.5 失敗時仍顯示 M3 LLM 推估（若有） |
| F-35.8 | **Provenance + 來源標示** | **P0** | Pro | UI：「LinkedIn 公開資料 · AI 整理 · n% · 日期」 |
| F-35.9 | M5「深入查此人」入口 | P1 | Pro | 結果卡觸發 M3.5；扣 quota |
| F-35.10 | 用户「不是此人 / 隱藏」 | P1 | Pro | 不寫入或清除 person 欄位；不再自動重試 |
| F-35.11 | Enterprise 團隊 quota / audit | P2 | Enterprise | 共享額度、操作 log |
| F-35.12 | Enterprise batch enrich | P2 | Enterprise | 明確 opt-in；非 MVP |

---

## L3.2 — 付費分層（DDR-74）

> **完整 Personal / Enterprise 对照**：`BSChat_PRD_v2.md` **§11.2.1 ~ §11.2.3**（Quota 均为 Pilot TBD）

| 能力 | Free | Pro | Enterprise Personal ※ |
|------|------|-----|------------------------|
| M3 LLM 推估 pass 1/2 | ✅ | ✅ | ✅ |
| M3.5 任何 API / worker | ❌ | ✅ | ✅ |
| 儲存 `linkedin_url`（不抓取） | ✅ | ✅ | ✅ |
| URL 自動 M3.5 | ❌ | ✅ 預設 on | ✅ |
| 手動 LinkedIn 補充 | ❌ | ✅ ※ | ✅ ※ |
| M5 深入查此人 | ❌ | ✅ 共用 person quota | ✅ |
| People API 供應商 | — | Pilot 選型 | 同 Pro + SLA |

※ **Enterprise Personal** = Phase 2 团队采购（Pool A），**不是** Enterprise Publisher（Pool B）。Quota 见 PRD §11.2.2。

**Free UX**：詳情顯示 M3「AI 推估」；LinkedIn 區顯示 **升級 CTA**，文案：「Pro：以 LinkedIn 公開資料核對職責範圍」。

---

## L3.3 — 資料流

### 3.3.1 自動（Pro + 有 linkedin_url）

```
[Contact upsert 含 linkedin_url]
        ↓
[M1 check: person_enrich_mode=linkedin_llm && auto_on_url]
        ↓
[Enqueue PersonEnrichJob trigger=url_auto]
        ↓
[Fetch profile via URL extract / People API]
        ↓
[match_score = 1.0 if URL exact]  // 無消歧
        ↓
[LLM summarize → person_scope, confidence]
        ↓
[Gate: score≥0.8 && conf≥0.75 → write person_enrichments + update display fields]
        ↓
[ContactIndexJob]
```

### 3.3.2 手動（Pro）

```
[User POST /contacts/:id/person-enrich]
        ↓
[Quota check → decrement person_linkedin_used]
        ↓
[Search: People API OR web search site:linkedin.com/in]
        ↓
[0 candidates → failed empty state]
[1 candidate → LLM]
[N candidates → return disambiguation UI; user picks → LLM]
        ↓
[User confirm OR auto if score≥0.8]
        ↓
[Write + re-index]
```

### 3.3.3 與 M3 合併顯示（詳情 ai_inferred）

| 情況 | 詳情顯示 |
|------|----------|
| Free | 僅 M3 `responsibility_scope`（conf≥0.6） |
| Pro，M3.5 成功 | **主顯示** LinkedIn 摘要；M3 推估可折疊「備用推估」 |
| Pro，M3.5 失敗 / 未跑 | 同 Free（M3 推估） |
| Pro，M3.5 候選待確認 | 顯示候選卡片 +「確認 / 不是此人」；不寫入 index |

---

## L3.4 — Match & Confidence Rules

| 規則 ID | 規則 |
|---------|------|
| R-35.1 | Free **不得** enqueue PersonEnrichJob（API + worker 雙重檢查） |
| R-35.2 | `match_score < 0.8` → **禁止**寫入 `contacts`  searchable 欄位 |
| R-35.3 | LLM `confidence < 0.75` → 不寫入；可展示「資訊不足」 |
| R-35.4 | 不覆寫 OCR `title`；可寫 `person_headline` 供參考 |
| R-35.5 | M3.5 結果寫入時 `provenance.source = linkedin`；M3 推估保留歷史 |
| R-35.6 | 用户「不是此人」→ status=rejected；不再自動重試 |
| R-35.7 | M5 `match_reason` 引用 person 欄位時須標「LinkedIn 公開資料」 |
| R-35.8 | 同一 contact 24h 内 duplicate manual job → idempotent 返回上次結果 |
| R-35.9 | People API 失敗 retry 2 次 → failed；不 fallback 到 scraping |

**match_score 計算（MVP）**：

```
score = 0.4 * name_sim + 0.35 * company_sim + 0.25 * title_sim
// 各 sim ∈ [0,1]；URL 完全匹配 → score = 1.0
```

---

## L3.5 — Entitlement（M1 契約）

```typescript
interface PersonEnrichEntitlement {
  person_enrich_mode: 'inference_only' | 'linkedin_llm';  // free | pro
  person_linkedin_quota_monthly: number;   // free=0, pro=20, enterprise=100|-1
  person_linkedin_used_this_month: number;
  person_linkedin_reset_at: string | null;
  person_linkedin_auto_on_url: boolean;    // pro default true
}
```

**GET /me** 回傳：

```json
{
  "person_enrich_mode": "inference_only",
  "person_linkedin_remaining_month": 0,
  "person_linkedin_auto_on_url": false
}
```

---

## L3.6 — API 概要

| Method | Path | 方案 | 說明 |
|--------|------|------|------|
| POST | `/contacts/:id/person-enrich` | Pro+ | 手動觸發；body 可含 `candidate_id`（消歧後） |
| GET | `/contacts/:id/person-enrich/status` | Pro+ | pending / completed / failed / needs_confirmation |
| POST | `/contacts/:id/person-enrich/confirm` | Pro+ | 用户確認候選 |
| POST | `/contacts/:id/person-enrich/reject` | Pro+ | 不是此人 / 隱藏 |
| — | Free 呼叫上述 | — | **403** `PERSON_ENRICH_NOT_ALLOWED` |

詳細 schema 見 `spec/architecture/BSChat_SA-SD_M35.md`。

---

## L3.7 — 資料來源策略（Pilot 選型）

**優先順序**（不自建 scraper）：

1. **名片/import 已有 `linkedin_url`** → URL extract（Tavily extract 或 People API by URL）
2. **无 URL** → 第三方 **People Enrichment API**（name + company + optional email）
3. **Fallback（P1）** → Web search `site:linkedin.com/in` + snippet only；**仅手动触发**

| 來源 | 自動 | 手動 | 備註 |
|------|------|------|------|
| linkedin_url direct | ✅ Pro | ✅ | 最準 |
| People API | ❌ MVP | ✅ | Pilot 测亚太命中率 |
| Tavily site: search | ❌ | P1 | 灰色；仅作 fallback |

**成本上限（Pilot 前假設）**：单次 person enrich ≤ **USD 0.35**；超過则 job failed + 不扣 quota（或 Pilot 後定）。

---

## L3.8 — UI 概要

### 詳情 — ai_inferred 區

**Free**：

```
┌─ AI 推估職責 ─────────────────────┐
│ 可能負責 OEM 通路與大客戶            │
│ ✦ AI 推估 · 67%                     │
└────────────────────────────────────┘
┌─ Pro 功能 ─────────────────────────┐
│ 🔒 以 LinkedIn 公開資料核對職責     │
│    [ 升級 Pro ]                     │
└────────────────────────────────────┘
```

**Pro — LinkedIn 成功**：

```
┌─ 職場公開資料（LinkedIn）──────────┐
│ 目前：OEM Sales Manager @ …         │
│ 可能負責：工業級 SSD 通路與 SI 伙伴  │
│ ✦ LinkedIn 公開資料 · AI 整理 · 82% │
│ 更新於 2026-05-20 · [不是此人]      │
└────────────────────────────────────┘
▸ 備用：AI 推估（來自名片職稱）…
```

### 候選消歧

```
找到 2 位可能匹配，請確認：
[ ] 王小明 · ABC Tech · OEM Manager     match 87%
[ ] 王小明 · ABC Technology · Sales    match 72%
[ 確認 ]  [ 都不是 ]  [ 取消 ]
```

---

## L3.9 — User Stories

**US-35.1 LinkedIn URL 自動補充（Pro）**

> As a Pro 業務, I want 電子名片上的 LinkedIn 連結自動整理成職責摘要, so that 我不必手動查 profile。

Acceptance:
- Given Pro + `person_linkedin_auto_on_url=true` + contact 有 valid linkedin_url, When upsert 完成, Then 背景 M3.5 job enqueue
- Given enrich 成功且 gate 通过, When 開詳情, Then 顯示 LinkedIn 區塊 + provenance

**US-35.2 手動補充（Pro）**

> As a Pro 業務, I want 對只有紙本職稱的聯絡人手動查 LinkedIn, so that 在 follow-up 前確認窗口。

Acceptance:
- Given quota>0, When POST person-enrich, Then 扣 1 次 quota
- Given quota=0, When POST, Then 429 `PERSON_LINKEDIN_QUOTA_EXCEEDED`

**US-35.3 Free 升級路徑**

> As a Free 使用者, I want 知道 Pro 能多做什么, so that 我可以決定是否升級。

Acceptance:
- Given Free, When 開詳情, Then 可見 M3 推估 + 升級 CTA；**不可見** LinkedIn 抓取結果
- Given Free POST person-enrich, Then 403 + 升級指引

**US-35.4 消歧與錯人防護**

> As a Pro 使用者, I want 系統在不确定时不擅自写入, so that 錯人資訊不會污染搜尋。

Acceptance:
- Given match_score=0.72, When job 完成, Then status=needs_confirmation；index **不含** person scope
- Given 用户 reject, When 再開詳情, Then LinkedIn 區隱藏；M3 推估仍可用

---

## L3.10 — 與上下游

```
Upstream
  M2 handoff（linkedin_url 字段）
  M1 entitlement
  M3 Contact 已存在

M3.5 輸出
  person_enrichments 表
  contacts.person_* 或增强 responsibility 显示字段
  ContactIndexJob

Downstream
  M5 搜索 / match_reason（person 欄位需 gate）
  M3 詳情 ai_inferred 分区（DDR-27 擴展）
```

---

## L3.11 — Pilot 驗證清單（🚧）

- [ ] 台湾 B2B 名片 20 张：People API 命中率、错人率
- [ ] 有 linkedin_url 5 张：URL extract 成功率
- [ ] 单次成本 vs Pro 定价（NT$299/月假设）
- [ ] 供应商合规条款（个资、存储期限）
- [ ] match_score 门槛 0.8 是否过严/过松

---

## L3.12 — 實作階段

| Phase | 内容 | 阻塞 |
|-------|------|------|
| **A** | M3 LLM pass 1/2（Free 路径） | M3.5 前置 |
| **B** | M1 entitlement 字段 + API gate | — |
| **C** | M3.5 URL auto + manual + UI | Pilot API |
| **D** | M5 深入查此人 + Enterprise quota | P1 |

---

*PM M3.5 v1.0 — SDLC Phase 1 · 付費個人 enrich*
