# BSChat PM L3 — Module 5：AI 搜尋（對話式找商機）

> **版本**：v1.1  
> **状态**：PM L3 ✅ 可锁定（MVP）；Phase 3 见附录  
> **依据**：`BSChat_PRD_v2.md` v2.2 §2/§11/§13、DDR-5/58~62、M3/M6 LOCKED 契约

---

## 模組定位

> M5 解決 Primary Persona 的**核心使用情境**（S-01）：  
> **「我現在要找什麼」→ 從已收錄名片庫反向找出公司對、人對的潛在商機。**

取代使用者現有流程：**Google 查公司類型 → 翻抽屜對名片 → 常對不上 → 放棄**。

**不是**：
- ❌ 固定「業務方向 profile」搜尋（DDR-5）
- ❌ 精確姓名/公司關鍵字搜尋器
- ❌ CRM pipeline 或商機管理
- ❌ 跨使用者/公開人脈搜尋（**MVP**；Phase 3 见附录 · Pool B）

**是**：
- ✅ 對話式、**即時意圖**的自然語言查詢
- ✅ 排序結果 + **每位匹配理由**（公司產品 + 個人職責）
- ✅ 以 M6 cache 為主、必要時 **query-time live 查**（DDR-34）
- ✅ 事件驅動；不要求養成每日使用習慣

**成功標準（S-01）**：從「開始搜尋」到「找到可聯絡對象」< **2 分鐘**。

---

## L3.1 — Sub-features

| # | Sub-feature | 優先 | 場景 | 驗收標準 |
|---|-------------|------|------|---------|
| F-5.1 | **對話式搜尋輸入** | **P0** | S-01 | 自然語言問句；無需設定 profile |
| F-5.2 | **混合檢索 + 排序** | **P0** | 全部 | 基於 index 召回 top-K → LLM rerank |
| F-5.2b | **多維度條件解析 + 硬約束過濾** | **P0** | DDR-73 | 從自然語言抽出公司/產業/場合/職能等；明確約束不滿足則排除，非僅職稱匹配 |
| F-5.3 | **匹配理由解釋** | **P0** | US-5.2 | 每位結果顯示「為何符合」 |
| F-5.4 | 搜尋結果 → 聯絡人詳情 | **P0** | S-04 | 帶 match context banner（M3 UI 預留） |
| F-5.5 | **空結果引導** | **P0** | N-02 | 0 結果時引導收錄/換問法，不責備 |
| F-5.6 | 含未確認聯絡人 | **P0** | DDR-22 | pending_review 可出現在結果 |
| F-5.7 | Aha 首次搜尋引導 | **P0** | DDR-10 | ≥3 張 index 後可搜；中性 placeholder + 首次成功 Aha modal |
| F-5.17 | **個人化搜尋建議**（靈感 chips） | P1 | DDR-71 | Pro：依已索引名片（公司產品、場合標籤等）動態生成；Free 不顯示 |
| F-5.8 | **Query-time live 查**（Layer 3） | **P1** | DDR-34/36 | 必要時 live 查公司；merge 不覆写 cache |
| F-5.9 | Live 查配額（Free/Pro） | P1 | PRD §11 | Free 每月 5 次；Pro 較高 |
| F-5.10 | 「採用本次查詢結果」→ M6 | P1 | DDR-36 | 用户 adopt → M6 query_adopt |
| F-5.11 | 搜尋 refinement 建議 | P1 | 原 PRD | 結果過多時建議縮小（活動/產業） |
| F-5.12 | 依 source_label 篩選 | P1 | S-02 | 「Computex 2026 認識的人」 |
| F-5.13 | 多輪對話上下文 | P1 | — | 同一 session 追問「只要 OEM 的」 |
| F-5.14 | pgvector 語意召回 | P1 | DDR-25 | MVP 可 tsvector-only；embedding P1 |
| F-5.15 | 搜尋歷史 | P2 | — | 近期查詢快速重跑 |
| F-5.16 | 一鍵複製聯絡方式 | **P0** | S-04 | 委派 **M8**；M5 結果卡含 CTA |

**明確不做（MVP）**：
- ❌ 固定儲存業務方向 / 搜尋 profile（DDR-5）
- ❌ Tags / Notes 搜尋（M3 P2）
- ❌ 跨 workspace / 團隊共享搜尋（Phase 2 Team；Phase 3 见 PRD §13）
- ❌ Live 查結果自動寫入 M6 cache（DDR-36）
- ❌ 搜尋結果匯出 CSV 給老闆（P2，訪談未選）

---

## L3.2 — 三層搜尋資料策略（與 M6 對齊）

```
Layer A — Index Cache（P0，Free + Pro）
  讀 M3 contact_search_documents
  字段：company_products(M6), responsibility_scope(M3), company/title, source_label, raw_text
  用途：主要召回與排序

Layer B — LLM Rerank + Explain（P0）
  Input：用户 query + top-K 候選 structured summary
  Output：排序 + 每人 match_reason（引用具體字段）

Layer C — Query-time Live（P1，Free 試用 / Pro 放寬）
  觸發：候選分數低 / 用户點「深入查詢」/ 明確問最新動態
  對 top 候選公司 live 查（复用 M6 pipeline 或轻量版）
  写入 query_augmentations；merge 展示；不覆写 M6 cache
  用户「採用」→ POST M6 enrich query_adopt
```

---

## L3.3 — 搜尋 Pipeline（產品邏輯）

```
[用户输入 query]
    │
    ▼
[Intent Parse]（LLM 或规则）
  · 提取维度：產業/產品、公司/生態、職能、活動、地區（若有）
  · 标注 hard vs soft：如「架構師就好」「只要 OEM」→ hard
  · 不持久化 profile（DDR-5）；不限于職稱字面（DDR-73）
    │
    ▼
[Retrieval — Layer A]
  · tsvector 全文（MVP P0）
  · optional pgvector cosine（P1）
  · filter: user_id, deleted_at IS NULL
  · boost: company_products, responsibility_scope, title, company_name, source_label
    │
    ▼
[Rerank + Hard Constraint Filter — Layer B]
  · LLM：对 top-K → 输出 top 5~10 + match_reason[]
  · **硬條件不滿足 → 不得進入 results**（DDR-73）
  · 跨欄位取證：職能←title∪responsibility_scope；產業←products∪company…
  · 低信心 inference 不得当作事实陈述（DDR-9）
    │
    ▼
{需要 Layer C?}
  · 是 → live 查（受 quota）→ merge cache_products + live_products
  · 否 → 直接返回
    │
    ▼
[SearchResults UI]
  · 结果卡：姓名、公司、匹配理由、信心提示
  · → 詳情（带 context）→ M8 複製
```

**何时触发 Layer C（P1 默认策略）**：

| 条件 | 行为 |
|------|------|
| top1 score < 阈值 | 自动 suggest live 查 |
| 用户点「深入查詢」 | 强制 live（扣 quota） |
| query 含「最新/最近/現在」 | 倾向 live |
| cache 已有高 confidence products | **不** live（节省成本） |

---

## L3.4 — State Machine

### Search Request

```
[SUBMITTED]
    → [PARSING_INTENT]
    → [RETRIEVING]        ← tsvector / vector
    → [RERANKING]         ← LLM
    → [COMPLETED]         ≥1 结果
    → [EMPTY]             0 结果
    → [FAILED]            API/DB 错误

可选分支（P1）：
[RERANKING] → [LIVE_AUGMENTING] → [COMPLETED|EMPTY]
```

### Search Session（P1 多轮）

```
session: active → closed（30min idle 或用户离开 Tab）
turns: [{ query, results, created_at }, ...]
```

MVP：**单轮 P0 足够 Aha**；session 表可预留，UI 先单轮。

---

## L3.5 — Data Entities

### SearchSession（P1；MVP schema 预留）

```
id, user_id, workspace_id
status              ← active|closed
turn_count
created_at, updated_at
```

### SearchQuery

```
id, session_id?, user_id
query_text
parsed_intent       ← jsonb { products[], roles[], events[], ... }
retrieval_mode      ← cache|cache+live
live_augmentation_used  ← bool
status              ← 见 state machine
result_count
latency_ms
created_at
```

### SearchResult（append-only per query）

```
id, query_id, contact_id
rank                ← 1..N
match_score         ← 0.0-1.0
match_reason        ← text（UI 显示）
match_sources       ← jsonb [{ field, value, confidence }]
  例：{ "field": "company_products", "value": "工業電腦", "confidence": 0.82 }
live_products       ← jsonb nullable（Layer C merge）
created_at
```

### QueryAugmentation（与 M6 SA/SD 共享；**M5 owner**）

```
id, user_id, company_id, query_id
live_products, source_urls, confidence
adopted             ← default false
created_at
```

---

## L3.6 — 匹配理由显示规则

| 匹配来源 | 显示格式 | 条件 |
|----------|----------|------|
| company_products | 「公司主要產品包含 {X}」 | M6 conf ≥ 0.5 |
| responsibility_scope | 「可能負責 {X}（AI 推估 · {n}%）」 | M3 conf ≥ 0.6 |
| title | 「職稱為 {X}」 | 有值 |
| company_name 模糊 | 「公司名稱與 {keyword} 相關」 | 弱匹配 |
| source_label | 「來源：{Computex 2026}」 | 用户 query 含活动 |
| live（P1） | 「本次查詢：公司產品包含 {X}」 | Layer C；标注「即時查詢」 |

**禁止**：
- 低信心（<0.6）推估写成肯定句
- 无依据的「可能认识」类话术

**範例（US-5.2）**：
> 符合原因：公司主要產品包含工業電腦主機；此人職稱為 OEM 業務經理（AI 推估 · 67%）

---

## L3.7 — Rules

| ID | 規則 |
|----|------|
| R-1 | **不儲存**固定業務方向；每次 query 獨立解析意圖（DDR-5） |
| R-2 | 搜尋範圍（MVP）= **Pool A** 当前 user 的 private 名片庫（M7）；**不**含他人私人库（DDR-59） |
| R-3 | `pending_review` / `auto_accepted` 皆可被索引與搜尋（DDR-22） |
| R-4 | 匹配理由必须引用 index 中实际字段；不可 hallucinate 产品 |
| R-5 | M6 products conf < 0.5 不得作为高信心匹配理由 |
| R-6 | M3 inference conf < 0.6 不得作为匹配理由（与 M3 一致） |
| R-7 | Layer C live 结果 **不自动** 写入 M6 cache（DDR-36） |
| R-8 | Cache-only 搜尋 P95 < **3s**；含 live P95 < **30s** |
| R-9 | 0 结果不得 empty blame；提供「收錄更多名片」CTA |
| R-10 | Free：cache 搜尋合理額度（建议 ≥30 次/日）；live **5 次/月** |
| R-11 | Pro：cache 较高额度；live 较高额度（Pilot 定） |
| R-12 | 首次搜尋 ≥1 结果 = **Aha Moment** 计数（DDR-10） |
| R-13 | 删除 Contact → 下次搜尋不得出现（M3 index 同步） |
| R-14 | 使用者**明確約束**（如「X 就好」「只要 X」）→ **硬條件**；不滿足不得返回（DDR-73） |
| R-15 | 條件比對**跨欄位**：職能←`title`∪`responsibility_scope`；產業←`company_products`∪`company_name`；場合←`source_label`（DDR-73） |
| R-16 | 禁止 `match_reason` 表述不符合卻仍列在結果中；寧可 NO_MATCH（DDR-73） |

---

## L3.8 — 与上下游边界

```
Upstream（M5 读取）
  M3 contact_search_documents  ← 主索引
  M3 contacts（详情跳转）
  M6 company_products（经 index 字段）
  M1 user_entitlements         ← live quota

M5 核心输出
  SearchResults + match_reason
  → M3 詳情（context banner）
  → M8 複製/致電

M5 → M6（P1）
  query_augmentations
  用户 adopt → CompanyEnrich query_adopt

M5 不拥有
  Contact 业务字段、enrichment cache、OCR 原文（只读 index）
```

---

## L3.9 — 5 Diagnostic Angles

### Upstream

| 來源 | 契約 |
|------|------|
| M3 index worker | `contact_search_documents` 及时更新 |
| M6 enrich | `company_products` 写入 index |
| M3 inference | `responsibility_scope` 写入 index |
| M2 handoff | `source_label`, `raw_text` |
| M1 | `user_id`, live/search quota |

### Downstream

| 模組 | 消費 |
|------|------|
| **M3 詳情** | match_reason context banner |
| **M8 行動** | 结果卡 copy phone/email |
| **M6 adopt** | query_augmentations.adopted |
| **M9** | search_submitted, search_result_clicked, aha_moment |

### Who-else（並發）

- 搜尋进行中 M6 enrich 完成 → index  eventual consistency；下次搜尋更新
- 用户快速连发两次 query → 独立 query_id；UI 显示最新
- live 查与 M6 manual refresh 同一公司 → 独立 storage，不冲突

### Failure

| 失敗 | 行為 | UX |
|------|------|-----|
| 0 contacts indexed | EMPTY + 引导收錄 | 「先收錄幾張名片」 |
| LLM rerank 失败 | fallback tsvector 排序 | 仍显示结果，理由简化 |
| live quota 用尽 | 仅 cache 结果 + CTA | 「本月即時查詢已用完」 |
| index 延迟 | 新 Contact 暂不可搜 | 「資料同步中，稍后再试」 |
| 全库无匹配 | EMPTY | 换问法建议 + 範例 query |

### Data-reuse

| 資料 | 用途 |
|------|------|
| company_products | 高权重匹配 + 理由 |
| responsibility_scope | 高权重（conf≥0.6） |
| source_label | 活动筛选 + 理由 |
| review_status | confirmed boost |
| field_confidences | 理由措辞强度 |
| enriched_at | P1「資料較舊」提示 |

---

## L3.10 — User Stories

**US-5.1 對話式找商機**
> As a B2B 業務代表, I want to 用自然語言問「我手上有誰做工業電腦的？」, so that 我不需要記得精確姓名或公司名也能找到潛在商機。

Acceptance Criteria:
- Given 名片庫 ≥3 笔已 index, When 输入「我手上有誰做 IPC 的？」, Then 返回排序结果 + 每人匹配理由
- Given 本季业务方向改变, When 输入新意图, Then **无需**修改任何 profile（DDR-5）
- Given 有 pending_review 联系人, When 搜尋, Then 仍可出现在结果中

**US-5.2 搜尋結果解釋**
> As a B2B 業務代表, I want to 看到系統為何回傳某個結果, so that 我能判斷是否 worth follow-up。

Acceptance Criteria:
- Given 返回 3 笔, When 查看任一结果, Then 显示匹配理由（产品 + 职称/推估）
- Given 推估 confidence < 0.6, When 生成理由, Then **不**以推估作为主要匹配依据

**US-5.3 空結果不放棄（N-02）**
> As a B2B 業務代表, I want to 搜尋沒結果時知道下一步, so that 我不會以為產品沒用。

Acceptance Criteria:
- Given 0 匹配, When 搜尋完成, Then 显示「試試換個說法」+ 範例 + 「去收錄名片」CTA
- Given 仅 1-2 张名片, When 搜尋, Then 可提示「再多收幾張，搜尋會更準」

**US-5.4 Aha 首次搜尋（DDR-10）**
> As a 新用戶, I want to 收錄幾張名片後立刻試搜, so that 我能在 10 分鐘內感受到價值。

Acceptance Criteria:
- Given ≥3 OCR 完成, When 进入搜尋 Tab, Then 显示範例 query + 可输入
- Given 首次 ≥1 结果, When 完成, Then 计 Aha moment（M9）

**US-5.5 即時深入查詢（P1，Free 試用 / Pro）**
> As a B2B 業務代表, I want to 在搜尋時必要時查最新公司資料, so that 過期 cache 不會讓我錯過商機。

Acceptance Criteria:
- Given cache 分数低, When 点「深入查詢」, Then live 查 + merge 显示（标注来源）
- Given 用户点「採用並儲存」, When 确认, Then 写入 M6 cache（query_adopt）
- Given Free 月度 live 5 次用尽, When 再请求, Then 403 + 升级 CTA

**US-5.6 找到後立刻行動（→ M8）**
> As a B2B 業務代表, I want to 从搜尋結果複製電話或 Email, so that 我可以立刻聯絡。

Acceptance Criteria:
- Given 搜尋結果卡, When 点複製, Then 复制成功 Toast（M8 P0）

---

## L3.11 — 付費分層（M5 部分）

| 能力 | Free | Pro |
|------|------|-----|
| Cache 搜尋（Layer A+B） | ✅ 建议 ≥30 次/日 | ✅ 较高 |
| 個人化搜尋建議（靈感 chips） | ❌ | ✅ P1（依索引名片推導） |
| Query-time live（Layer C） | 5 次/月 | 较高（Pilot 定） |
| 多轮对话（P1） | ✅ | ✅ |
| 搜尋历史（P2） | — | P2 |

M1 管 quota 字段；M5 读取 `EntitlementService`（同 M6 模式，DDR-39 stub）。

---

## L3.12 — UI 约束（移交 UI/UX）

**搜尋 Tab 默认**（Design Foundation §2.2）

| 元素 | 規則 |
|------|------|
| 输入框 | 多行 textarea；**中性 placeholder**（如「用自然語言描述你要找的人或情境…」） |
| 靈感 chips | **MVP 不顯示**；Pro P1 見 F-5.17 / DDR-71 |
| 可搜尋人數 | 顯示 **「X 位可搜尋」**（= Pool A `indexed_count`）；**不**並列「已索引 vs 聯絡人總數」（DDR-72） |
| 送出 | Primary；loading typing indicator |
| 结果列表 | Contact 卡 + match_reason 区块 |
| 空状态 | 引導收錄或換問法（`suggestions` 文案）；**不用**通用產業範例 chips |
| 0 结果 | 换问法 + 收錄 CTA |
| Privacy Strip | 常显「預設私人」 |

**从 M5 进详情**：顶部 Context Banner「符合原因：…」（M3 UIUX 已预留）

---

## DDR（M5 模組）

| ID | 決策 |
|----|------|
| DDR-51 | MVP 检索 = tsvector + LLM rerank；pgvector P1 |
| DDR-52 | 单轮搜尋 P0；多轮 session P1 |
| DDR-53 | match_reason 必须结构化来源字段，禁止幻觉 |
| DDR-54 | Layer C 默认手动触发；低分 auto-suggest（P1） |
| DDR-55 | 0 结果 = 产品机会，必须引导收錄/换问法 |
| DDR-56 | confirmed contact +10% rank boost |
| DDR-57 | 搜尋不锁 Free 基本 cache 能力（Aha Moment） |
| DDR-58 | Pool A/B 分离；MVP 仅 A（见 PRD §13） |
| DDR-59 | 禁止搜他人私人收錄聯絡人 |
| DDR-71 | MVP 不顯示通用靈感 chips；Pro 個人化建議依索引名片推導（見 PRD v2） |
| DDR-72 | UI 用「可搜尋」= Pool A indexed_count；庫外/Pool B 不共用「已索引」；刪除聯絡人同步遞減（見 PRD v2） |
| DDR-73 | 多維度查詢條件 + 硬/軟約束；跨欄位匹配；不符合不返回（見 PRD v2） |

*DDR-5/34/36/70 见 PRD v2；DDR-25 见 M3 SA/SD*

---

## Open Blockers → SA/SD

| 🚧 | 議題 |
|----|------|
| B-7 | MVP tsvector-only vs 启用 pgvector |
| B-11 | Layer C 自动触发阈值与成本上限 |
| B-12 | 多轮 context window 与 session 存储 |
| B-13 | Rerank prompt 与 match_reason JSON schema |
| B-14 | 中文分词 / pg_trgm 策略（延续 M3 风险） |

**SA/SD 已解**：B-7 ✅ tsvector-only MVP · B-11 ✅ Layer C 阈值 · B-12 ✅ 单轮 P0 · B-13 ✅ JSON schema · B-14 ✅ pg_trgm fallback

---

## Success Metrics（M5）

| 指標 | MVP 目標 | 依據 |
|------|---------|------|
| 搜尋 P95（cache） | < 3s | R-8 |
| 搜尋 → 有结果 | > 60% 首次 | DDR-10 Aha |
| 搜尋 → 点击详情 | > 40% 有结果 session | engagement |
| 搜尋 → 聯絡（M8） | > 30% | S-04 |
| 匹配理由满意度 | > 3.5/5 | DDR-9 |

---

## Coupling Check

| 模組 | M5 依赖 / 约束 |
|------|----------------|
| **M3** | index 及时；detail context banner |
| **M6** | company_products in index；query_adopt API |
| **M2** | source_label, raw_text in index |
| **M8** | 结果卡行动 CTA |
| **M1** | search/live quota |
| **M7** | user-scoped only；private 永不进 Pool B |

---

## 附录 — Phase 3：M5b 跨池搜尋（PRD §13 · 不阻塞 MVP）

> **产品决策（v2.2）**：不搜别人的人脉；只搜**自愿公开**的商務身份。  
> 企业合作：Enterprise 订阅 → M11 建立员工公开商務身份 → 进入 **Pool B**；**Pro** 可搜。

### 两个搜索池

| Pool | 内容 | MVP | Phase 3 |
|------|------|-----|---------|
| **A — Private Rolodex** | 自己收錄的名片 | ✅ M5 P0 | ✅ |
| **B — Public Directory** | 企业/个人自愿公开的商務身份 | ❌ | ✅ M5b + M11 |

### Phase 3 Sub-features（规划）

| # | Sub-feature | 优先 |
|---|-------------|------|
| F-5.17 | `search_scope`：private / network / all | P3 |
| F-5.18 | 结果分来源标注（你的库 vs 公开池 · 公司名） | P3 |
| F-5.19 | Pro 跨池搜尋 quota（M1） | P3 |
| F-5.20 | Free 时 teaser「公开池有 N 条匹配，升级 Pro」 | P3 optional |

### Phase 3 Rules

| ID | 规则 |
|----|------|
| R-P3-1 | private contact **永不**写入 public index（DDR-62） |
| R-P3-2 | Pool B 实体由 M11 创建，与 M3 private contact **分离** |
| R-P3-3 | 员工下架 → 24h 内从 Pool B index 移除 |
| R-P3-4 | Free **只搜 Pool A**；Pro / 企業版 可含 Pool B（DDR-61） |

### MVP 预留（SA/SD 低成本）

```typescript
// SearchRequest — MVP 默认
search_scope: 'private'  // Phase 3: 'network' | 'all'

// SearchResult — MVP 默认
source_pool: 'private_rolodex'  // Phase 3: 'public_directory'
publisher_org_id?: string
```

### 模块耦合（Phase 3）

| 模块 | 关系 |
|------|------|
| **M11** | Pool B 数据 owner；企业电子名片 CRUD + 发布 |
| **M1** | `plan_tier`: free / pro / enterprise |
| **M5b** | 跨池检索 + rerank + explain（复用 Layer A/B pipeline） |
| **M6** | 公开池公司资料 enrich（可共享 pipeline） |

*完整愿景：`BSChat_PRD_v2.md` §13、§11.5*

---

**M5 PM L3：✅ 可鎖定**

---

### 🤝 Handoff: PM → SA/SD — Module 5：AI 搜尋

**SA/SD 必須交付**：
1. 检索架构（tsvector / pgvector / 混合）— 解 🚧 B-7
2. Search API + query/result schema
3. LLM rerank + explain pipeline — 解 🚧 B-13
4. Layer C live 与 M6 接口 — 解 🚧 B-11
5. L4 Depth Gate 五项 + Coupling Map 更新
6. 与 `contact_search_documents` 读取契约

---

*PM M5 L3 v1.0 — SDLC Phase 1*
