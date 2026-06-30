# BSChat PM L3 — Module 5：AI 搜尋（對話式找商機）

> **版本**：v1.2  
> **状态**：PM L3 ✅ 可锁定（MVP + Stage 1b 規格）；M5b 跨池已實作  
> **依据**：`BSChat_PRD_v2.md` **v2.5** §2/§11.8~9/§13、DDR-5/58~62/73/96~100、M3/M6 LOCKED 契约

---

## 模組定位

> M5 解決 Primary Persona 的**核心使用情境**（S-01）：  
> **「我現在要找什麼」→ 從已收錄名片庫反向找出公司對、人對的潛在商機。**

取代使用者現有流程：**Google 查公司類型 → 翻抽屜對名片 → 常對不上 → 放棄**。

**不是**：
- ❌ 固定「業務方向 profile」搜尋（DDR-5）
- ❌ 精確姓名/公司關鍵字搜尋器
- ❌ CRM pipeline 或商機管理
- ❌ 跨 workspace / 團隊共享搜尋（Phase 2 Team）
- ❌ 固定儲存業務方向 / 搜尋 profile（DDR-5）；**允許**持久化 `search_precision`（DDR-97）

**是**：
- ✅ 對話式、**即時意圖**的自然語言查詢
- ✅ 排序結果 + **每位匹配理由**（公司產品 + 個人職責）
- ✅ 以 M6 cache 為主、必要時 **query-time live 查**（DDR-34）
- ✅ **Pro+** 跨池搜尋（Pool A + 公開 stub）；結果標來源（DDR-80）
- ✅ 使用者可調 **搜尋精準度**（Account Hub · §11.9）；Free 分級開放（DDR-98）
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
| F-5.14 | pgvector 語意召回 | P1 | DDR-25 | 見 **F-5.22**；MVP tsvector-only |
| F-5.15 | 搜尋歷史 | P2 | — | 近期查詢快速重跑 |
| F-5.16 | 一鍵複製聯絡方式 | **P0** | S-04 | 委派 **M8**；M5 結果卡含 CTA |
| F-5.18 | **搜尋精準度偏好**（strict / balanced / exploratory） | **P0** | US-5.3、§11.9 | Account Hub 持久化；Free 禁 exploratory；注入 **rerank prompt**（DDR-101） |
| F-5.19 | **結果可信度**（禁 fallback 湊數 + degraded 路徑） | **P0** | DDR-99 | Rerank 無合格 → EMPTY；`degraded` 不套用探索門檻 |
| F-5.20 | **match_sources chips** + 來源 pool badge | **P0** | DDR-100、US-5.2 | 「你的名片庫」vs「公開商務 · {公司}」；欄位 chip |
| F-5.21 | **跨池搜尋 UX**（Pro+ 預設 `all`） | **P0** | Stage 2 | 一次搜尋混排；結果頁 client 篩選（全部/僅我的/僅公開） |
| F-5.22 | pgvector + 混合召回（RAG） | P1 | DDR-25、§11.9 Stage 2 | tsvector + embedding + RRF；多切片待企業內容變厚 |

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
[Retrieval — Layer A]（统一漏斗 · DDR-101）
  · LLM 精炼 intent → 混合召回 top-K（`RETRIEVAL_TOP_K=50` / 池；禁止按库大小分叉）
  · tsvector + pg_trgm（MVP）；+ pgvector RRF（P1）
  · filter: user_id / published stub；产出 retrieval_score
    │
    ▼
[Rerank — Layer B]
  · LLM：对 top-K → 输出 top 5~10 + match_score + match_reason + match_sources[]
  · **search_precision** → rerank prompt 严格度（§11.9；**不**服务端 min_match_score 过滤）
  · **硬條件不滿足 → 不得進入 results**（DDR-73）
  · **禁止 retrieval fallback 湊數**（DDR-99）：无 LLM 合格输出 → EMPTY
  · 跨欄位取證；低信心 inference 不得当作事实陈述（DDR-9）
    │
    ▼
[SearchResults UI]
  · 结果卡：来源 badge + match_reason + **match_sources chips**（DDR-100）
  · degraded → 明显 banner「簡化模式」（非仅小字）
  · Pro+：混排 private + public；结果页可选筛选
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
parsed_intent       ← jsonb { products[], roles[], events[], hard_*[], ... }
search_scope        ← private | network | all（Pro+ 默认 all）
retrieval_mode      ← cache|cache+live
live_augmentation_used  ← bool
status              ← 见 state machine
result_count
latency_ms
degraded            ← LLM 离线路径
suggest_live
created_at
```

### SearchResult（append-only per query）

```
id, query_id, contact_id?, stub_id?
rank                ← 1..N
match_score         ← 0.0-1.0
match_reason        ← text（UI 显示）
match_sources       ← jsonb [{ field, value, confidence }]
source_pool         ← private_rolodex | public_directory
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
| R-2 | 搜尋範圍：Free = Pool A only；**Pro+** = Pool A +（可选）Pool B；`search_scope` 默认 all（Pro+） |
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
| R-17 | **`search_precision` 可持久化**（Account Hub）；**≠** 業務方向 profile（DDR-97） |
| R-18 | Free 仅可选 strict / balanced；exploratory 需 Pro+（DDR-98） |
| R-19 | rerank 无输出或 hard constraint 后 0 条 → **EMPTY**；禁止 retrieval 模板 fallback 凑数（DDR-99）；**禁止**以 `match_score` 硬门槛 silent 丢弃 LLM 结果（DDR-101） |
| R-20 | `degraded=true` 时 UI 必须标注简化模式；fallback 路径之 score 仅供参考（DDR-100） |
| R-21 | Pro+ 默认 `search_scope=all`；结果必须标注 source_pool（DDR-80） |

---

## L3.8 — 与上下游边界

```
Upstream（M5 读取）
  M3 contact_search_documents  ← 主索引
  M3 contacts（详情跳转）
  M6 company_products（经 index 字段）
  M1 user_entitlements         ← live/search quota；search_precision

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
| M1 | `user_id`, live/search quota, **search_precision** |

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
| LLM rerank 失败 | `degraded=true`；仍可用 mock 路径时 **不** 硬塞低分结果 | banner「簡化模式」；不套用探索门槛（DDR-99） |
| 精準模式 0 结果 | EMPTY + 建议改平衡/探索(Pro) | 不降低门槛 silent 返回 |
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
- Given 结果含 match_sources, When 查看结果卡, Then 显示字段 chip（DDR-100）
- Given 公开池结果, When 显示, Then badge「公開商務 · {公司}」且无电话/Email（DDR-80）

**US-5.3 搜尋精準度偏好（Account Hub · PRD §11.9）**
> As a B2B 業務代表, I want to 在「我的」設定搜尋要多精準, so that 我可以自己決定結果要嚴格還是寬鬆。

Acceptance Criteria:
- Given Free, When 设定 search_precision, Then 仅 strict / balanced 可存；exploratory → 403 或降 balanced（QA 锁定）
- Given Pro, When 选 exploratory, Then rerank prompt 允许弱相关；仍禁 retrieval 模板 fallback（DDR-99、DDR-101）
- Given strict 且无匹配, When 搜尋, Then EMPTY + 建议改平衡或（Pro）探索
- Given degraded=true, When 搜尋, Then 不套用 exploratory 门槛
- Given 变更 precision, When PATCH settings, Then 不写入业务方向 profile（DDR-5）

**US-5.4 空結果不放棄（N-02）**
> As a B2B 業務代表, I want to 搜尋沒結果時知道下一步, so that 我不會以為產品沒用。

Acceptance Criteria:
- Given 0 匹配, When 搜尋完成, Then 显示「試試換個說法」+ 範例 + 「去收錄名片」CTA
- Given 仅 1-2 张名片, When 搜尋, Then 可提示「再多收幾張，搜尋會更準」

**US-5.5 Aha 首次搜尋（DDR-10）**
> As a 新用戶, I want to 收錄幾張名片後立刻試搜, so that 我能在 10 分鐘內感受到價值。

Acceptance Criteria:
- Given ≥3 OCR 完成, When 进入搜尋 Tab, Then 显示範例 query + 可输入
- Given 首次 ≥1 结果, When 完成, Then 计 Aha moment（M9）

**US-5.6 即時深入查詢（P1，Free 試用 / Pro）**
> As a B2B 業務代表, I want to 在搜尋時必要時查最新公司資料, so that 過期 cache 不會讓我錯過商機。

Acceptance Criteria:
- Given cache 分数低, When 点「深入查詢」, Then live 查 + merge 显示（标注来源）
- Given 用户点「採用並儲存」, When 确认, Then 写入 M6 cache（query_adopt）
- Given Free 月度 live 5 次用尽, When 再请求, Then 403 + 升级 CTA

**US-5.7 找到後立刻行動（→ M8）**
> As a B2B 業務代表, I want to 从搜尋結果複製電話或 Email, so that 我可以立刻聯絡。

Acceptance Criteria:
- Given 搜尋結果卡, When 点複製, Then 复制成功 Toast（M8 P0）

---

**US-5.8 跨池搜尋（Pro+ · Stage 2 已實作）**
> As a Pro 使用者, I want to 一次搜尋同時看到我的名片庫與公開商務身份, so that 我不必先选 pool 再搜两次。

Acceptance Criteria:
- Given Pro, When 搜尋, Then 默认 search_scope=all；结果混排并标注来源
- Given 混合结果, When 列表, Then 可选 client 筛选（全部/僅我的/僅公開）
- Given Free, When search_scope=network|all, Then 403 SEARCH_SCOPE_NOT_ALLOWED

---

## L3.11 — 付費分層（M5 部分 · 对齐 PRD §11.3 D / §11.9）

| 能力 | Free | Pro | 企業版 |
|------|:----:|:---:|:------:|
| Cache 搜尋（Layer A+B） | ✅ ≥30 次/日 | ✅ 较高 | ✅ 最高 |
| 搜尋精準度：精準 / 平衡 | ✅ | ✅ | ✅ |
| 搜尋精準度：探索 | 🔒 预览+CTA | ✅ | ✅ |
| 自訂 min_match_score 滑桿 | ❌ | ❌ | 🚧 Admin 组织默认 P2 |
| 個人化搜尋建議 chips | ❌ | ✅ P1 | ✅ |
| 跨池搜尋（Pool B） | ❌ | ✅ | ✅ |
| Query-time live（Layer C） | 5 次/月 | 较高 | 较高 |
| match_sources chips + 禁 fallback | ✅ | ✅ | ✅ |
| 多轮对话（P1） | ✅ | ✅ | ✅ |
| 搜尋历史（P2） | — | P2 | P2 |

**Account Hub 搜尋偏好**（M1 UI · M5 消费）：见 PRD §11.8~9；设置页非搜尋 Tab。

M1 管 quota + `search_precision`；M5 读取 `EntitlementService` + user settings（DDR-39 stub）。

---

## L3.12 — UI 约束（移交 UI/UX · 含 Stage 1b）

**搜尋 Tab 默认**（Design Foundation §2.2）

| 元素 | 規則 |
|------|------|
| 输入框 | 多行 textarea；**中性 placeholder** |
| 搜尋前 scope tab | **不显示**（Pro+ 默认 all；DDR-96 后 UX 决策） |
| 靈感 chips | MVP 不显示；Pro P1 见 F-5.17 / DDR-71 |
| 可搜尋人數 | Pool A `indexed_count`；Pro+ 另列公开商务人数（DDR-72） |
| 结果列表 | 来源 badge + Contact/stub 卡 + match_reason + **match_sources chips** |
| 结果筛选 | Pro+ 有结果后：全部 / 僅我的 / 僅公開（client-side） |
| degraded | **Banner**「簡化模式，結果僅供參考」+ 小字 latency（DDR-100） |
| 空状态 | 引導收錄或换问法；精準模式 EMPTY 可建议改平衡/升级 Pro |
| Privacy Strip | 常显「預設私人」 |

**Account Hub「我的 → 搜尋偏好」**（M1 页面 · M5 字段）

| 元素 | 規則 |
|------|------|
| 三档选择 | 精準 / 平衡 / 探索（segmented control） |
| Free 探索 | 可见 locked + Pro CTA 文案（DDR-98） |
| 说明 | 一句解释「不影响你每次输入的搜尋内容，只调整结果严格度」 |

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
| DDR-58 | Pool A/B 分离；**M5b 跨池已实作**（Pro+） |
| DDR-59 | 禁止搜他人私人收錄聯絡人 |
| DDR-71 | MVP 不顯示通用靈感 chips；Pro 個人化建議依索引名片推導（見 PRD v2） |
| DDR-72 | UI 用「可搜尋」= Pool A indexed_count；庫外/Pool B 不共用「已索引」；刪除聯絡人同步遞減（見 PRD v2） |
| DDR-73 | 多維度查詢條件 + 硬/軟約束；跨欄位匹配；不符合不返回（見 PRD v2） |
| DDR-96~100 | Account Hub、搜尋精準度分級、禁 fallback、match_sources / degraded UI（PRD §11.8~9） |
| DDR-M5-01 | Pro+ 默认 search_scope=all；搜尋 Tab 不放 scope 切换器 |
| DDR-M5-02 | ~~search_precision → min_match_score~~ **已废止** → 改 **search_precision → rerank prompt**（DDR-101） |
| DDR-M5-03 | **两种分数分工**：`retrieval_score`（召回排序）vs `match_score`（rerank 排序/展示/QA）；均不得作 EMPTY 硬门槛（DDR-101） |

*DDR-5/34/36/70/80 见 PRD v2.5；DDR-25 见 M3 SA/SD*

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

## 附录 A — M5b 跨池搜尋（**Stage 2 已實作** · PRD §13）

> **状态（2026-06-16）**：后端 M5b + M11 Pool B 已实作；Pro+ `search_scope=network|all`；UI 混排 + 结果筛选。

### 两个搜索池

| Pool | 内容 | 状态 |
|------|------|------|
| **A — Private Rolodex** | 自己收錄的名片 | ✅ |
| **B — Public Directory** | 企业 Admin 发布的公开商务 stub | ✅ M11 MVP |

### 已实现 Sub-features

| # | Sub-feature | 状态 |
|---|-------------|------|
| F-5.21 | Pro+ 默认 `search_scope=all`；结果标注 source_pool | ✅ |
| F-5.20 | 私人「你的名片庫」/ 公开「公開商務 · {公司}」badge | ✅ |
| — | 结果页 client 筛选（全部/僅我的/僅公開） | ✅ |
| F-5.19 | 禁 fallback 硬塞（Stage 1b 待实作） | 🚧 |
| F-5.18 | Account Hub search_precision | 🚧 Stage 1b |

### Phase 3 Rules（仍有效）

| ID | 规则 |
|----|------|
| R-P3-1 | private contact **永不**写入 public index（DDR-62） |
| R-P3-2 | Pool B 实体由 M11 创建，与 M3 private contact **分离** |
| R-P3-3 | 员工下架 → 24h 内从 Pool B index 移除 |
| R-P3-4 | Free **只搜 Pool A**；Pro / 企業版 可含 Pool B（DDR-61） |

### 模块耦合

| 模块 | 关系 |
|------|------|
| **M11** | Pool B owner |
| **M1** | plan_tier + search_precision entitlement |
| **M5b** | 跨池检索 + rerank + explain（复用 Layer A/B） |

---

## 附录 B — Stage 1b 交付范围（Next）

| 项 | 模块 | 说明 |
|----|------|------|
| 关 fallback + EMPTY 诚实化 | M5 ENG | DDR-99 |
| match_sources chips + degraded banner | M5 UI | DDR-100 |
| Account Hub 搜尋偏好 | M1 UI + API | `PATCH /me/settings` |
| search_precision → rerank prompt | M5 ENG | 读 user settings（DDR-101） |
| PM/QA 用例 | M5 QA | Free/Pro precision matrix |

*完整愿景：`BSChat_PRD_v2.md` §11.8~9*

---

**M5 PM L3：✅ 可鎖定（v1.2）**

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

*PM M5 L3 v1.2 — 2026-06-16 · 对齐 PRD v2.5（Account Hub + 搜尋精準度 + Stage 1b）*
