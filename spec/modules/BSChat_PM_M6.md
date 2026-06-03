# BSChat PM L3 — Module 6：公司資訊補全（Enrichment）

> **版本**：v1.1（含動態資料策略 + 付費分層）  
> **狀態**：PM L3 ✅ 可鎖定  
> **依據**：PRD v2.1、M3 LOCKED 契約、訪談 + 產品策略討論

---

## 模組定位

> M6 解決使用者**最大放棄點**（N-01）：「看不出這家公司做什麼」。  
> 將「Google 查公司」自動化，補上 **主要產品/服務**，供 M3 詳情、M5 搜尋、M3 職責推估 pass 2 使用。

**資料策略（v1.1 修正）**：非「掃一次永久正確」，而是 **Cache-at-ingest + Query-time refresh（M5）+ Pro 自動過期刷新**。

---

## L3.1 — Sub-features

| # | Sub-feature | 優先 | 說明 |
|---|-------------|------|------|
| F-6.1 | 公司實體解析（Company Resolution） | **P0** | 從 `company_name` 建立/匹配 Company |
| F-6.2 | **主要產品/服務補全** | **P0** | 訪談「夠用標準」第一項 |
| F-6.3 | 公司官網辨識 | **P0** | enrich 主要來源 |
| F-6.4 | 欄位級 Provenance + 信心度 | **P0** | 來源 URL、confidence、`enriched_at` |
| F-6.5 | 背景非同步 Enrich Job | **P0** | 不阻塞收錄/瀏覽 |
| F-6.6 | 使用者接受 / 拒絕 / 覆寫 | **P0** | DDR-9 信任機制 |
| F-6.7 | 多 Contact 共享 Company | **P0** | 同公司 enrich 一次 |
| F-6.8 | `CompanyEnriched` event → M3 | **P0** | inference pass 2 + re-index |
| F-6.9 | **手動「更新公司資訊」** | P0 Free 限額 / Pro 放寬 | 见付费分层 |
| F-6.10 | **過期自動 refresh** | **P1 Pro 专属** | M1 开关；M6 scheduler 执行 |
| F-6.11 | 公司簡介（1–2 句） | P1 | |
| F-6.12 | 產業/類別標籤 | P1 | M5 refinement |
| F-6.13 | 多候選公司消歧 UI | P1 | MVP 最佳努力 + 低信心 |
| F-6.14 | 地區 / 規模 | P2 | |

**明确不做（MVP）**：
- ❌ 人員在職狀態追蹤（DDR-33）
- ❌ **個人 LinkedIn 搜尋 / 同步**（改由 **M3.5** Pro/Enterprise 負責；M6 僅公司官網 enrich）

---

```
Layer 1 — Cache-at-ingest（M6，P0，Free+Pro）
  收錄 → Contact 建立 → 背景 enrich 一次 → 寫入 Company
  用途：名片庫列表/詳情立刻「看懂公司」

Layer 2 — Stale Auto-refresh（M6 scheduler，P1，Pro 专属）
  enriched_at > N 天（默认 90，Pro 可调 30/60/90）
  M1 读取 entitlement → M6 背景 re-enrich

Layer 3 — Query-time Web Augmentation（M5，P0/P1）
  使用者搜尋/問 AI 時，必要時 live 查网
  合并 cache + 本次查询结果 → 排序 + 解释
  不自动覆写 M6 cache，除非用户「采用本次结果」（DDR-36）
```

### M1 vs M6 职责

| M1 账号/订阅 | M6 Enrich |
|-------------|-----------|
| 方案 tier（Free/Pro） | enrich pipeline |
| `auto_refresh_enabled` 开关 | stale 扫描 cron |
| 手动 refresh 月度配额 | 网页抓取 + LLM |
| 用量显示 | CompanyEnriched event |

---

## L3.3 — 与 M3 边界

```
M3 Contact 建立（company_name 有值）
    → CompanyEnrichRequested
M6 Worker
    → Company + Enrichment + enriched_at
    → contacts.company_id
    → CompanyEnriched（若 DDR-31 条件满足）
M3：inference pass 2 + re-index
M3.5（Pro）：LinkedIn 個人補充 — 见 `BSChat_PM_M35.md`；**不经过 M6 pipeline**
M3 详情：company_enrichment 区块（已有 UIUX spec）
```

---

## L3.4 — State Machine

### Enrich Job

```
[REQUESTED] → [RESOLVING] → [ENRICHING]
    → [COMPLETED]   products conf ≥ 0.5
    → [PARTIAL]     有官网但 products 低
    → [FAILED]
    → [NEEDS_REVIEW]  P1 多候选
```

### 触发类型（`trigger_type`）

| 值 | 触发 |
|----|------|
| `ingest` | 收录时（Free+Pro） |
| `manual` | 用户点更新（受配额限制） |
| `stale_auto` | Pro 过期自动（M1 开关 ON） |
| `company_name_changed` | M2/M3 修改公司名 |

### 用户审核状态

`auto | accepted | rejected | user_override`  
**reject 后不因 re-enrich 自动复活**（DDR-32），除非用户点「重新补全」。

---

## L3.5 — Data Entities

### Company

```
id, user_id                    ← MVP 不跨 user 共享
normalized_name, display_name
website_url
enrich_status                  ← never|pending|completed|partial|failed
last_enriched_at               ← enriched_at（DDR-35）
enrich_version
```

### CompanyEnrichment（append-only）

```
id, company_id, enrich_version
main_products                  ← P0 核心
summary, industry_tags         ← P1
fields_provenance              ← jsonb per field
overall_confidence
trigger_type                   ← ingest|manual|stale_auto|...
model, prompt_version
status, created_at
```

### UserSettings（M1 schema 预留，M6 读取）

```
user_id
plan_tier                      ← free|pro
auto_refresh_enabled           ← Pro only，默认 false
auto_refresh_interval_days     ← 30|60|90，默认 90
manual_refresh_quota_monthly   ← Free: 3, Pro: unlimited
manual_refresh_used_this_month
```

---

## L3.6 — 显示规则

| 条件 | UI |
|------|-----|
| products conf ≥ **0.5** | 显示产品 + `✦ AI 补全 · 来源 · XX%` + `更新于 YYYY-MM-DD` |
| conf **0.3–0.49** | 「资讯不足，建议确认公司名称」 |
| conf **< 0.3** | 「无法取得公开资讯」 |
| enriching | `⏳ 正在补充公司资讯...` |
| rejected | 隐藏产品区 |
| override | 用户值 + 「已修正」 |

**CompanyEnriched 触发（DDR-31）**：
`status ∈ {completed, partial}` AND `main_products` 非空 AND confidence ≥ 0.5

---

## L3.7 — Rules

| ID | 规则 |
|----|------|
| R-1 | Enrich 完全背景，不阻塞 M2/M3 |
| R-2 | 同 Company 24h 内不重复 enrich（除非 name/website 变更或 manual/stale） |
| R-3 | 多 Contact 共享同一 Company enrich |
| R-4 | company_name 变更 → re-enrich |
| R-5 | 重名公司 P1 消歧；MVP 最佳努力 + 低信心 |
| R-6 | 找不到官网 → 不脑补产品 |
| R-7 | provenance 不可改；override 叠加 |
| R-8 | 用户数据不用于模型训练 |
| R-9 | Enrich SLA P95 < 30s |
| R-10 | 每 user 每日 enrich quota（可配置） |
| R-11 | **职位/在职以名片快照为准**；UI 标「名片资料 · 收录于 [date]」 |
| R-12 | **Pro auto_refresh 仅 M1 开关 ON 时执行** |
| R-13 | **M5 live 查结果不自动覆写 cache**（DDR-36） |

---

## L3.8 — 5 Diagnostic Angles

### Upstream
- M3：`CompanyEnrichRequested`
- M1：`plan_tier`, `auto_refresh_enabled`, quotas
- 公开 Web + LLM（B-3 → SA/SD）

### Downstream
- M3 详情、inference pass 2
- M5 index + query-time augmentation
- M5 解释：「公司主要产品包含 XXX」

### Who-else
- 同 company 并发 handoff → job dedupe by company_id
- reject vs enrich 完成 → 用户操作优先
- M5 live 查 vs M6 cache → 分离存储，用户可选采用

### Failure
- 找不到官网 / LLM 低信心 → partial/failed，不猜错
- quota 超出 → delayed queue
- Pro 降级为 Free → 停止 stale scheduler，保留已有 cache

### Data-reuse
- `company_id`, `main_products[]`, `enriched_at`, `fields_provenance` → M3/M5/M1

---

## L3.9 — User Stories

**US-6.1** 主要产品自动补全（收录时，Free+Pro）  
**US-6.2** 接受/拒绝/覆写 AI 补全  
**US-6.3** 列表一眼看懂公司（ContactListCard AI 摘要）  
**US-6.4** 补全完成触发 M3 inference pass 2  
**US-6.5** Pro 用户开启自动更新过期公司资料（M1 设置 → M6 执行）  
**US-6.6** 手动更新公司资讯（Free 每月 3 次 / Pro 不限）

---

## DDR（M6 模块）

| ID | 决策 |
|----|------|
| DDR-28 | MVP 核心字段 = main_products + website |
| DDR-29 | 显示门槛 products conf ≥ 0.5 |
| DDR-30 | Company 按 user_id + normalized_name 去重 |
| DDR-31 | CompanyEnriched 触发条件（见 L3.6） |
| DDR-32 | reject 后不自动复活 |
| DDR-33 | MVP 不追踪人员在职；名片为交换快照 |
| DDR-34 | Cache-at-ingest + Query-time（M5）混合 |
| DDR-35 | 必须带 enriched_at；UI 显示更新时间 |
| DDR-36 | M5 live 查不自动覆写 M6 cache |
| DDR-37 | 过期 auto refresh = Pro 功能 |
| DDR-38 | M1 管 entitlement；M6 管执行 |
| DDR-39 | MVP hardcode plan=free；schema 预留 Pro 字段 |

---

## Open Blockers → SA/SD

| 🚧 | 议题 |
|----|------|
| B-3 | 网页抓取 + LLM pipeline 选型 |
| B-6 | 多候选消歧 MVP 范围 |
| B-8 | stale scheduler cron + entitlement 检查接口 |

---

*PM M6 L3 v1.1 — SDLC Phase 1*
