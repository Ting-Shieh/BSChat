# BSChat PM L3 — Module 3：聯絡人結構化與索引

> **版本**：v1.0（2026-05-20 補寫；對齊已 LOCKED 的 M3 SA/SD / UI/UX / ENG / QA）  
> **狀態**：PM L3 ✅ 可鎖定  
> **依據**：`BSChat_PRD_v2.md` §1.4 DDR-7/8/9、§5 P0 M3、US-6.2（職責推估）、M2 Handoff、M5/M6 契約

---

## 模組定位

> M3 是 **M2 收錄 → M5 搜尋 / M6 補全** 之間的**結構化與信任層**。  
> 把 OCR 結果變成一致的 **Contact 模型**，並在**不要求使用者補備註**的前提下，AI 推估「這個人可能負責什麼」（DDR-8）。

**「夠用」標準的一半在 M3**（DDR-7）：

```
公司主要產品（M6） + 個人負責業務（M3 推估） = 值得 follow-up
```

**使用者不需要操作建檔** —— M2 handoff 後 Contact **自動出現**在名片庫；背景跑 inference + index。

**付費分層（DDR-74）**：M3 LLM 推估为 **Free + Pro 共用**。Pro/Enterprise 的 **LinkedIn + LLM 個人補充** 由 **M3.5** 负责，见 `spec/modules/BSChat_PM_M35.md`；M3 不因付費而停用。

```
M2 Handoff（OCR / Review）
        ↓
M3 Upsert Contact + Provenance
        ├─→ M6 CompanyEnrichRequested（有 company_name）
        ├─→ Inference pass 1（title + company）
        └─→ ContactIndexJob → contact_search_documents
                ↓
M6 CompanyEnriched → Inference pass 2 → re-index
                ↓
M5 讀 index 搜尋 · UI 三區塊詳情
```

---

## L3.1 — Sub-features

| # | Sub-feature | 優先 | 場景 | 驗收標準 |
|---|-------------|------|------|---------|
| F-3.1 | **M2 Handoff → Contact Upsert** | **P0** | 全部收錄 | 30s 內出現在名片庫 |
| F-3.2 | **字段 Provenance 追蹤** | **P0** | DDR-9 信任 | 每字段 source + confidence |
| F-3.3 | **名片庫列表** | **P0** | 瀏覽人脈 | 分頁、縮圖、AI 摘要列 |
| F-3.4 | **詳情三區塊** | **P0** | DDR-27 | card_original / ai_inferred / company_enrichment |
| F-3.5 | **職責推估 pass 1** | **P0** | DDR-8 | title + company → scope（conf≥0.6 才显示） |
| F-3.6 | **職責推估 pass 2** | **P0** | US-6.2 | M6 products 就緒後更新；supersede pass 1 |
| F-3.7 | **搜尋索引寫入** | **P0** | M5 前置 | `contact_search_documents` + tsvector |
| F-3.8 | 列表 AI 摘要（推估 or M6 產品） | **P0** | 看懂公司/人 | conf 門檻同詳情 |
| F-3.9 | **軟刪除 + M2 cascade** | **P0** | M7 隱私 | DELETE → DeleteCardCascade |
| F-3.10 | M5 Context Banner 入口 | **P0** | S-04 | from_search 參數 + match_reason |
| F-3.11 | Reject AI 推估 | P1 | 不信任 AI | 推估區消失；status=rejected |
| F-3.12 | 手動編輯字段 + override | P1 | 糾正 OCR | provenance→manual；company 變更重觸 M6 |
| F-3.13 | 列表篩選/排序 | P1 | 展後整理 | source_label、review_status |
| F-3.14 | 簡單前缀搜索（列表 q） | P1 | 記得姓名 | GET /contacts?q= |
| F-3.15 | Tags / Notes | P2 | 原 PRD | MVP 不做 |
| F-3.16 | M4 重複提示消費 | P1 | dedup | DuplicateSuspected 事件 |
| — | **M3.5 LinkedIn 個人補充** | Pro | DDR-74 | 见 `BSChat_PM_M35.md`；**非 M3 范围** |

**明確不做（MVP）**：
- ❌ 使用者必填備註/分類（DDR-11 在 M2）
- ❌ 人員在職狀態追蹤（DDR-33）
- ❌ Tags / Notes 搜尋（M5 P2）
- ❌ 團隊共享 Contact（Phase 後）
- ❌ CSV 直接匯入 Contact（走 M2 P2）

---

## L3.2 — Contact 生命週期

### 3.2.1 建立（自動）

```
[M2 ContactUpsertRequested]
        ↓
[UPSERT contacts]（idempotent by raw_card_id）
        ├─ provenance from OCR
        ├─ review_status ← M2 auto_accepted | unconfirmed
        ├─ search_status = pending_index
        ├─ IF company_name → CompanyEnrichRequested → M6
        ├─ Enqueue inference pass 1
        └─ Enqueue contact-index
        ↓
[ACTIVE] — 列表可見、M5 可索引（index 完成後）
```

### 3.2.2 更新

| 触发 | 行为 |
|------|------|
| M2 review PATCH（三栏） | Upsert 更新 name/company/title |
| M6 CompanyEnriched | pass 2 inference + re-index |
| 用户 PATCH company_name | manual override + 重触发 M6 |
| 用户 reject inference | scope 清空；不再显示 |

### 3.3.3 删除

```
[用户 DELETE]
        ↓
soft-delete（deleted_at）
        ↓
DeleteCardCascade → M2 原图
        ↓
删除 contact_search_documents
        ↓
M5 下次搜尋不出现
```

---

## L3.3 — State Machine

### Contact.search_status

```
pending_index → indexed
              ↘ index_failed（retry，不阻塞 ACTIVE）
```

### responsibility_inferences

```
pass 1 / pass 2 产生
        ↓
active（conf ≥ 0.6 写入 contacts + UI 显示）
        ↓
superseded（pass 2 更高 conf）
        ↓
rejected（用户 reject）
```

### review_status（来自 M2，M3 只读展示 + 列表 badge）

```
unconfirmed | confirmed
```

---

## L3.4 — 詳情三區塊（DDR-27）

| 區塊 | 内容 | 来源 |
|------|------|------|
| **card_original** | 姓名、公司、职称、电话、Email、地址、website、名片原图 | OCR（M2） |
| **ai_inferred** | responsibility_scope + confidence + 「AI 推估」 | M3 inference |
| **company_enrichment** | main_products、官网、provenance | M6（M3 聚合展示） |

**显示规则**：

| 条件 | UI |
|------|-----|
| inference conf ≥ **0.6** | 显示 ai_inferred 区 |
| inference conf < 0.6 | **不渲染** ai_inferred（宁缺勿滥，DDR-9） |
| M6 pending | company_enrichment 显示「補全中」 |
| M6 failed / 无 products | 区块 failed 或隐藏 products |
| 用户 reject inference | ai_inferred 整区隐藏 |

**列表 AI 摘要优先级**（与 M6 UIUX 对齐）：
1. `responsibility_scope`（conf ≥ 0.6）
2. else `company_products_preview`（M6，conf ≥ 0.5）
3. else 不显示 AI 摘要行

---

## L3.5 — 職責推估（Inference）

### Pass 1（Contact 创建后）

- **Input**：`title`, `company_name`
- **Output**：`inferred_scope`, `confidence`
- **Gate**：conf < 0.6 → 不写入 `contacts.responsibility_scope`；UI 不显示

### Pass 2（M6 enrich 后 · DDR-26）

- **触发**：`CompanyEnriched` 且 `main_products` 非空且 conf ≥ 0.5
- **Input**：title, company, **company_products**
- **行为**：若新 conf > pass 1 → supersede pass 1；re-index

### 文案

- 显示：「可能負責 {scope} · AI 推估 · {n}%」
- **禁止**写成肯定句（「負責 OEM 通路」无标注）

---

## L3.6 — 搜尋索引（M5 前置 · DDR-25）

M3 **拥有** `contact_search_documents`；M5 **只读**。

**search_text 拼接**（index worker）：
```
display_name | company_name | title | responsibility_scope | source_label | phones | emails | company_products(M6)
```

**触发 re-index**：
- Contact upsert
- Inference 写入 scope
- CompanyEnriched（products 更新）
- 用户 PATCH 影响搜尋字段
- Contact DELETE → 删 document

**MVP**：tsvector；`embedding` 字段预留（M5 P1 pgvector）。

**权重建议**（移交 M5）：products / scope 高；confirmed +10% boost。

---

## L3.7 — Rules

| ID | 規則 |
|----|------|
| R-1 | Handoff **幂等**：同一 `raw_card_id` → UPDATE not duplicate |
| R-2 | Inference conf **< 0.6** 不得写入 Contact 或 UI（DDR-9） |
| R-3 | Pass 2 **仅**在 M6 products 非空时运行（DDR-26） |
| R-4 | `unconfirmed` Contact **仍**写入 index、**可**被 M5 搜（DDR-22） |
| R-5 | 缺 name+company 仍 CREATE；`display_name` 可「未命名」 |
| R-6 | 详情/API **分区**展示；不混用 OCR 与 AI 字段（DDR-27） |
| R-7 | 用户 manual 编辑 → provenance=manual；保留 override 历史 |
| R-8 | `company_name` 变更 → emit `CompanyEnrichRequested` |
| R-9 | DELETE soft-delete；hard-delete 由 M7 cascade |
| R-10 | 跨 user 访问 Contact → 404 |
| R-11 | 不追踪在职/离职（DDR-33） |
| R-12 | index 失败不阻塞 Contact 列表可见；search_status 重试 |
| R-13 | M5 from_search 详情须显示 SearchContextBanner |

---

## L3.8 — 与上下游边界

```
Upstream
  M2 ContactUpsertRequested（主入口）
  M6 CompanyEnriched（pass 2 + re-index）
  M4 DuplicateSuspected（P1）

M3 核心输出
  contacts + provenance + inferences
  contact_search_documents
  GET /contacts API

Downstream
  M5 读 index
  M6 读 company_name → enrich
  M8 详情复制电话/Email
  M2 DeleteCardCascade
  M9 contact_viewed, inference_rejected（stub）
```

**M3 不拥有**：OCR 原文（读 M2）、enrichment cache（读 M6）、搜尋排序逻辑（M5）。

---

## L3.9 — 5 Diagnostic Angles

### Upstream

| 來源 | 契約 |
|------|------|
| M2 handoff | raw_card_id, fields, confidences, source_label, review_status |
| M6 | CompanyEnriched payload |
| M1 | user_id, workspace_id |

### Downstream

| 模組 | 消費 |
|------|------|
| **M5** | contact_search_documents |
| **M6** | company_name, website, CompanyEnrichRequested |
| **M8** | phones, emails on detail |
| **M2** | DeleteCardCascade |

### Who-else（並發）

- M2 review PATCH 与 M3 详情 PATCH → version 409
- pass 1 与 pass 2 并发 → pass 2 supersede
- enrich 与 index → eventual consistency

### Failure

| 失敗 | 行為 |
|------|------|
| handoff 格式错误 | DLQ；M2 卡片仍可见 |
| inference API 失败 | 留空 scope；不显示推估区 |
| M6 超时 | Contact active；enrichment pending |
| index 失败 | search_status retry；M5 可能暂缺 |

### Data-reuse

| 資料 | 用途 |
|------|------|
| title + company | pass 1 inference |
| + products | pass 2 inference |
| responsibility_scope | 列表摘要、M5 index、match_reason |
| source_label | 列表 badge、M5 筛选 P1 |
| review_status | badge、M5 boost |
| provenance | 详情信任、M5 explain |

---

## L3.10 — User Stories

**US-3.1 自動建檔**
> As a B2B 業務代表, I want to 名片收進來後自動出現在名片庫, so that 我不需要手動建立聯絡人。

Acceptance Criteria:
- Given M2 OCR 完成, When 30s 内, Then Contact 出现在 `/contacts` 列表
- Given auto_accepted 或 pending_review, When 列表, Then 皆可浏览

**US-3.2 看懂三層資訊（DDR-27）**
> As a B2B 業務代表, I want to 在詳情清楚區分名片原文與 AI 資訊, so that 我知道哪些是 OCR、哪些是推估。

Acceptance Criteria:
- Given 打开详情, When 渲染, Then 三区块 card_original / ai_inferred / company_enrichment 分区
- Given OCR 字段, When 显示, Then 标注来源与 confidence

**US-3.3 個人負責業務推估（= PRD US-6.2 · M3 拥有）**
> As a B2B 業務代表, I want to 看到 AI 推估這個人可能負責哪塊業務, so that 即使我當初沒有記下來，仍能判斷是否為正確窗口。

Acceptance Criteria:
- Given 职称 + M6 产品就绪, When conf ≥ 0.6, Then 显示推估 + 「AI 推估 · n%」
- Given conf < 0.6, When 显示, Then **不**显示推估区
- Given M6 enrich 完成, When pass 2 更高 conf, Then 更新 scope 并 re-index

**US-3.4 名片庫瀏覽**
> As a B2B 業務代表, I want to 瀏覽所有收錄的聯絡人, so that 我可以快速掃描誰可能是潛在窗口。

Acceptance Criteria:
- Given ≥1 Contact, When 名片库 Tab, Then 列表含姓名、公司、职称、AI 摘要（若有）
- Given 0 Contact, When 名片库 Tab, Then 空状态引导收錄

**US-3.5 搜尋索引就緒（M5 前置）**
> As a 产品, I want to Contact 变更后更新搜尋索引, so that M5 对话搜尋能命中最新資料。

Acceptance Criteria:
- Given Contact upsert, When index job 完成, Then contact_search_documents 存在
- Given CompanyEnriched, When re-index, Then search_text 含 company_products

**US-3.6 刪除聯絡人**
> As a B2B 業務代表, I want to 刪除不需要的聯絡人, so that 我的名片庫保持可控且符合隱私預期。

Acceptance Criteria:
- Given 确认删除, When DELETE, Then 列表不可见；M2 原图 cascade；M5 不再命中

**US-3.7 拒絕 AI 推估（P1）**
> As a B2B 業務代表, I want to 標記 AI 推估不準確, so that 錯誤資訊不會影響我的判斷。

Acceptance Criteria:
- Given reject inference, When POST, Then ai_inferred 区隐藏；inference status=rejected

**US-3.8 從搜尋進入詳情（M5 整合 · P0）**
> As a B2B 業務代表, I want to 从搜尋結果進詳情時看到符合原因, so that 我能確認為何這個人被推薦。

Acceptance Criteria:
- Given from_search query param, When 详情, Then SearchContextBanner 显示 match_reason

---

## L3.11 — UI 约束（移交 UI/UX · 已 LOCKED）

| 元素 | 規則 |
|------|------|
| ContactListCard | 缩图 + AI 摘要 + source badge + 未确认 badge |
| 详情 | 三区块垂直排列；M6 区块见 M6 UIUX |
| reject | P1：推估区 footer「不準確」 |
| 编辑 | P1：sheet 编辑；company 变更提示 re-enrich |
| 空状态 | 「去收錄」CTA |

---

## DDR（M3 模組 · 与 SA/SD 对齐）

| ID | 決策 |
|----|------|
| DDR-25 | MVP 索引 = PostgreSQL tsvector；pgvector 预留 |
| DDR-26 | Pass 2 仅 M6 products 非空时 |
| DDR-27 | 详情三区块 API/UI 分区 |
| DDR-8 | 职责推估 = AI；不要求用户当场补充 |
| DDR-9 | conf < 0.6 不显示推估 |
| DDR-22 | unconfirmed 仍可被 M5 索引 |
| DDR-33 | 不追踪在职状态 |

*M3 SA/SD 另见 DDR-21（M2 handoff）*

---

## Open Blockers（已解 · 补录）

| 🚧 | 議題 | 狀態 |
|----|------|------|
| B-2 | Inference prompt / 模型 | ✅ SA/SD §5；conf 0.6 |
| B-2b | Pass 2 触发条件 | ✅ DDR-26 |

---

## Success Metrics（M3）

| 指標 | MVP 目標 | 依據 |
|------|---------|------|
| Handoff → 列表可见 | < 30s | SA/SD |
| Inference 显示率 | 有 title 的 Contact 中 > 40% conf≥0.6 | 产品观察 |
| Index 完成率 | > 95% contacts indexed | M5 前置 |
| 推估 reject 率 | < 15%（过高则调 prompt） | DDR-9 |
| 详情三区块理解度 | 用户测试 qualitative | DDR-27 |

---

## Coupling Check

| 模組 | M3 依赖 / 约束 |
|------|----------------|
| **M2** | ContactUpsertRequested；DeleteCardCascade |
| **M6** | EnrichRequested / CompanyEnriched |
| **M5** | index write；Context Banner |
| **M8** | 详情行动 |
| **M4** | DuplicateSuspected P1 |
| **M7** | soft-delete；privacy |

---

## 下游文件对齐（补写后完整）

| 文件 | 状态 |
|------|------|
| `BSChat_SA-SD_M3.md` | ✅ v1.0 LOCKED |
| `BSChat_UIUX_M3.md` | ✅ v1.0 LOCKED |
| `BSChat_ENG_M3.md` | ✅ v1.0 LOCKED |
| `BSChat_QA_M3.md` | ✅ v1.0 LOCKED |
| **`BSChat_PM_M3.md`** | **✅ v1.0（本文）** |

**M3 六角色规格完整 · 🔒 LOCKED**

---

*PM M3 L3 v1.0 — SDLC Phase 1 补写*
