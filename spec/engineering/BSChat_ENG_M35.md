# BSChat ENG — Module 3.5：個人公開資料補充（LinkedIn + LLM）

> **依據**：`BSChat_SA-SD_M35.md` v1.1（DDR-81~85）、`spec/product/BSChat_M35_data_source.md`、PRD §12.5 / §11.3 C
> **技術棧**：FastAPI · SQLAlchemy 2 async · Alembic · Celery · Anthropic / Gemini（與 repo LOCKED stack 一致；**非** M6 ENG 文件的 TS/Prisma 寫法）
> **狀態**：v1.0（2026-06-11 補寫，回填既有實作 + 對齊 data_source 決議）
> **前置**：M1 entitlement（`person_enrich_mode` / quota）· M2 handoff `linkedin_url` · M3 `responsibility_scope` · M6 `main_products`（唯讀）

---

## 1. 技術選型（M3.5 增量）

| 層級 | 選型 | 用途 |
|------|------|------|
| **候選解析** | People Search provider（`person_search_provider`：`mock` → 上線換真 provider） | 無 URL 時找 LinkedIn 候選 |
| **LinkedIn 抓取** | `person_linkedin_web.py`（Gemini Google Search fallback） | 有 URL 取公開摘要 |
| **LLM 摘要** | `person_enrich_provider`：`gemini`（預設 `gemini-2.5-flash`）/ `claude` | `person_scope` 結構化輸出 |
| **背景佇列** | Celery task `person.enrich`（僅 url_auto） | 收錄後自動補充 |
| **額度** | `core/entitlements.py`（月額度 reset + consume） | Pro LinkedIn quota |

### 環境變數（`backend/.env.example` 對應）

```bash
PERSON_ENRICH_USE_MOCK=false
PERSON_ENRICH_PROVIDER=gemini            # gemini | claude | mock（LLM summarize）
PERSON_SEARCH_PROVIDER=mock              # mock | linkedin（官方 API，尚未接）
PERSON_LINKEDIN_WEB_FALLBACK=true        # 對使用者提供的 URL 用 Gemini Google Search
GEMINI_PERSON_MODEL=gemini-2.5-flash
PERSON_ENRICH_MODEL=claude-sonnet-4-20250514
PERSON_MATCH_GATE=0.8
PERSON_CONFIDENCE_GATE=0.75              # linkedin_url | people_api
PERSON_CONFIDENCE_GATE_WEB=0.70         # web_search on known LinkedIn URL
PERSON_CONFIDENCE_GATE_CARD=0.65        # card_inference fallback
```

> 🚩 **紅旗 2（上線阻擋）**：`PERSON_SEARCH_PROVIDER=mock` 時嚴禁輸出 `linkedin_profile` / `linkedin_search`，只能 `card_inference` / `unavailable`（見 §4.3、§7）。

---

## 2. 後端結構（實際檔案）

```
backend/app/
├── modules/m3_5_person/
│   ├── __init__.py
│   ├── service.py                 # 編排：quota → resolve → match gate → LLM → confidence gate → write → re-index
│   └── section_builder.py         # 詳情 sections.person_enrich 狀態機
├── ai/
│   ├── pipelines/
│   │   ├── person_enrich.py       # PersonCandidate / fetch_by_url / search_people /
│   │   │                          #   summarize_person_scope / build_card_inference_candidate / person_search_is_mock
│   │   └── person_linkedin_web.py # 有 URL 的公開摘要抓取（Gemini Google Search）
│   └── schemas/person_scope_output.py  # LLM 輸出 schema（scope + confidence）
├── models/person_enrich.py        # PersonEnrichJob / PersonEnrichment
├── schemas/contact.py             # PersonEnrichSection / *Request / *Response
├── api/v1/contacts.py             # 4 endpoints（見 §3）
├── workers/tasks/person_enrich.py # Celery task person.enrich（url_auto）
└── core/
    ├── entitlements.py            # is_person_enrich_allowed / person_linkedin_remaining /
    │                              #   consume_person_linkedin_quota / reset_person_linkedin_quota_if_needed
    └── config.py                  # person_* 設定（§1）

backend/alembic/versions/009_m35_person_enrich.py   # schema migration
```

---

## 3. API 規格（`/api/v1`）

manual / confirm / from_search **同步執行**整條 pipeline，回 `200` 帶終態（非 202 queued）；僅 `url_auto` 走 Celery。

| Method | Path | 說明 | Auth |
|--------|------|------|------|
| POST | `/contacts/{id}/person-enrich` | 觸發 manual（有候選歧義回 `needs_confirmation`） | Pro+ |
| POST | `/contacts/{id}/person-enrich/confirm` | 確認候選 index（不另扣額度） | Pro+ |
| GET | `/contacts/{id}/person-enrich/status` | 查詢目前狀態 | Pro+ |
| POST | `/contacts/{id}/person-enrich/reject` | 「不是這個人」→ 清 person_scope + re-index | Pro+ |

**Response（`PersonEnrichResponse`）關鍵欄位**：`status`、`person_scope`、`confidence`、`match_score`、`data_source`、`provenance_label`、`candidates`、`quota_remaining`、`message`。

**Errors**：

| Code | HTTP |
|------|------|
| `PERSON_ENRICH_NOT_ALLOWED` | 403（Free） |
| `PERSON_LINKEDIN_QUOTA_EXCEEDED` | 429 |
| `PERSON_ENRICH_IN_PROGRESS` | 409 |
| `NO_PENDING_CANDIDATES` / `INVALID_CANDIDATE_INDEX` | 409 / 400 |

---

## 4. 核心流程

### 4.1 編排（`service.start_person_enrich`）

```
gate (is_person_enrich_allowed) → load contact → in-progress 檢查
→ 有 linkedin_url?
   ├─是→ fetch_by_url → None? → insufficient(unavailable)   [DDR-83]
   └─否→ search_people
          ├─0 筆 → build_card_inference_candidate (skip match gate)  [DDR-82]
          ├─>1 筆 → needs_confirmation
          └─1 筆 → process
→ match gate (非 card_inference 且 < 0.8) → needs_confirmation
→ summarize_person_scope → confidence gate（依來源 0.75/0.70/0.65）
   ├─未達 → insufficient（不扣額度）
   └─達 → _write_result（扣額度規則見 4.2）→ enqueue contact index
```

### 4.2 額度（`_uses_linkedin_quota`，DDR-84）

| 情況 | 扣 LinkedIn 額度 |
|------|:--:|
| `url_auto` | 否 |
| `card_inference` / `user_manual` | 否 |
| `linkedin_url` / `people_api`（有 URL） | 是 |
| manual + 原有 URL + `web_search` | 是 |

manual 觸發前若 contact 已有 URL，先 `reset_person_linkedin_quota_if_needed` 並檢查 remaining，0 → 429。

### 4.3 來源映射（`person_data_source` / `person_provenance_label`）

對外標籤一律由 `source_type` 經映射產生（見 SA-SD §2.5），**禁止寫死**。`person_search_is_mock()` 為 true 時，`card_inference` 標籤追加「（開發環境未接 LinkedIn API）」。

### 4.4 詳情區塊（`section_builder.build_person_enrich_section`）

狀態機回傳 `PersonEnrichSection`：`locked`(Free) / `completed` / `insufficient` / `needs_confirmation` / `rejected` / `pending` / `never`。`completed` 帶 `data_source` + `provenance_label`；各狀態帶 `has_m3_fallback`（DDR-81 分區，UI 上方顯示「系統參考（名片推估）」）。

---

## 5. 前端（`frontend/features/person-enrich/`）

```
features/person-enrich/
├── api.ts                       # 4 endpoints client
├── hooks.ts                     # useMutation / useQuery（invalidate ['contacts', id]）
├── components/PersonEnrichBlock.tsx   # 全狀態渲染 + 來源標籤 + 升級 CTA
└── index.ts
```

- **分區呈現（DDR-81）**：`PersonEnrichBlock` 為獨立區塊；M3 推估在其上方標「系統參考（名片推估）」。
- **標籤**：直接渲染 API `provenance_label`，不在前端拼字串（避免再次冒充）。
- **Free**：`status=locked` → 顯示升級 CTA，不打 enrich API。

---

## 6. Sprint Ticket（回填 + 收尾）

> 多數已實作（未提交）；本清單標已完成 / 待補。

| ID | Ticket | 狀態 |
|----|--------|------|
| M35-001 | migration 009 + models（PersonEnrichJob/Enrichment、contacts/entitlements 欄位） | ✅ 已實作 |
| M35-002 | service 編排（gate/resolve/match/confidence/write/reindex） | ✅ 已實作 |
| M35-003 | data_source 6 類映射 + provenance label | ✅ 已實作 |
| M35-004 | section_builder 全狀態 | ✅ 已實作 |
| M35-005 | 4 endpoints + schemas | ✅ 已實作 |
| M35-006 | Celery person.enrich（url_auto） | ✅ 已實作 |
| M35-007 | entitlements quota（reset/consume/remaining） | ✅ 已實作 |
| M35-008 | 前端 PersonEnrichBlock + hooks + api | ✅ 已實作 |
| **M35-009** | **接官方 LinkedIn API（取代 mock）** | ⛔ 擱置（API 待審核未過） |
| **M35-010** | **mock 防冒充硬化**：`person_data_source` 降級保險（mock 時 linkedin_*→card_inference）+ 移除死碼 `_mock_url_candidate`/`_slug_to_headline` + 單元測試 | ✅ 已完成 |
| M35-011 | 回歸：無 URL 重補 → 標「名片推估」（單元測試覆蓋） | ✅ 已完成（DB 整合測試待 Postgres 環境） |
| M35-012 | git commit（目前全部未提交） | ⏳ 待辦 |

> **M35-009 擱置說明**：官方 LinkedIn API 審核未過。Pro 上線資料來源＝有 URL → Gemini 公開搜尋（`linkedin_url_public`）、無 URL → `card_inference`；mock 路徑經 §4.3 降級保險確保**永不**出現 ✦ LinkedIn。待 API 過審再實作 `_fetch_by_url_linkedin` 並把 `PERSON_SEARCH_PROVIDER` 切 `linkedin`。

---

## 7. Definition of Done — M3.5

- [ ] Free 觸發 → 403 + 升級 CTA；不打外部 API
- [ ] `PERSON_SEARCH_PROVIDER=mock` → Pro 結果只能 `card_inference` / `unavailable`，UI 無 ✦ LinkedIn（紅旗 2）
- [ ] 有 URL 讀不到 → `insufficient` + `unavailable` + 提示，不扣額度（DDR-83）
- [ ] 無 URL 搜不到 → `card_inference`（≥0.65 才寫入），不扣額度（DDR-82/84）
- [ ] `completed` 必有 `person_scope`（禁止空 completed）
- [ ] `data_source` 與 `provenance_label` 一致且來自映射（DDR-85）
- [ ] 詳情與 M3 推估分區呈現（DDR-81）
- [ ] match < 0.8（非 card_inference）→ needs_confirmation，不寫入
- [ ] 僅 LinkedIn 路徑成功才扣 `person_linkedin` 月額度

---

## 8. 測試要點（供 QA）

| 區域 | 關鍵斷言 |
|------|---------|
| Gate | Free POST → 403；Pro 額度 0 → 429 |
| Mock 防冒充 | mock provider → 不得出現 `linkedin_profile/linkedin_search` |
| URL 讀不到 | fetch_by_url None → `unavailable`/`insufficient`，額度不變 |
| 無 URL 搜不到 | → `card_inference`；conf 0.6 → insufficient、0.7 → completed |
| confidence 分級 | linkedin 路徑 0.74 → insufficient；card 0.66 → completed |
| 額度 | linkedin_profile 成功扣 1；card_inference / url_auto 不扣 |
| 消歧 | >1 候選 → needs_confirmation → confirm 不另扣 |
| 一致性 | API `data_source` 對應 `provenance_label` |
| 分區 | 詳情 person_enrich 與 responsibility_scope 不混區 |
| Index | completed 後 search_text 含 person_scope |

**Mock 策略**：LLM / search provider 注入 mock；不依賴外網。

---

## 9. ENG 新增 DDR

| ID | 決策 |
|----|------|
| DDR-86 | M3.5 後端用 Python/FastAPI/SQLAlchemy/Celery（對齊 repo LOCKED stack；M6 ENG 文件的 TS/Prisma 描述視為過時，不適用本模組） |
| DDR-87 | manual/from_search 同步執行（request 內）；僅 url_auto 走 Celery，降低狀態輪詢複雜度 |
| DDR-88 | 對外標籤一律經 `person_data_source()` / `person_provenance_label()` 映射，禁止 endpoint/前端寫死 |

---

### 🤝 Handoff: ENG → QA — Module 3.5

**State Tracker**：

| 模組 | PM | SA/SD | UI/UX | ENG | QA |
|------|:--:|:-----:|:-----:|:---:|:--:|
| M3.5 | ✅ v2（DDR-81~85） | ✅ v1.1 | ⏳ | ✅ v1.0（回填） | ⏳ |

**上線阻擋**：M35-009/010（接真 provider + mock 防冒充）。
**Mock 策略**：search/LLM provider 注入；紅旗 2 必測。

---

*ENG M3.5 v1.0 — 2026-06-11 補寫（回填既有實作 + data_source 對齊）*
