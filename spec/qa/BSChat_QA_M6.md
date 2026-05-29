# BSChat QA — Module 6：公司資訊補全（Enrichment）

> **依據**：M6 PM L3 v1.1、M6 SA/SD v1.0、M6 UI/UX v1.0、ENG M6、PRD v2 DDR-28~39  
> **測試框架**：Vitest · Testing Library · Playwright · axe-core  
> **M6 估算**：P0 案例 32 条 · P1 案例 16 条

---

## 1. 測試策略

### 1.1 測試目標

| 目標 | 說明 |
|------|------|
| **看懂公司** | enrich 後主要產品可見；解決 N-01 放棄點 |
| **寧缺勿濫** | conf < 0.5 不顯示 products；< 0.3 / 無官網 → failed |
| **背景非阻塞** | enrich 不阻斷收錄/瀏覽；Contact 仍可用 |
| **共享去重** | 同 user 同公司 enrich 一次；多 Contact 共享 |
| **AI 透明** | provenance、confidence、`enriched_at` 必顯示 |
| **信任機制** | reject 不復活；override 疊加；re-enrich 可恢復 |
| **付費配額** | Free manual 3 次/月；Pro auto_refresh（stub） |
| **M3 整合** | CompanyEnriched → pass 2 + re-index |
| **安全** | 跨用户隔离；SSRF 防護 |

### 1.2 測試金字塔（M6）

```
        ┌─────────┐
        │ E2E   7 │  ingest→enrich→详情→reject/refresh
        ├─────────┤
        │ Int  18 │  worker pipeline, gate, quota, events
        ├─────────┤
        │ Unit 22 │  normalize, section builder, discovery
        └─────────┘
```

| 層級 | 工具 | M6 覆蓋 |
|------|------|---------|
| Unit | Vitest | `normalizeCompanyName`, `CompanyEnrichmentSectionBuilder`, conf gate |
| Integration | Vitest + test DB + HTML fixture | enrich worker mock LLM, dedupe, entitlement |
| Component | Testing Library | `CompanyEnrichmentBlock` 全狀態、`CompanyProductsPreview` |
| E2E | Playwright + worker mock | 详情 pending→completed、manual refresh |
| Manual | 清單 | 真實官網抓取抽樣 10 家 TW B2B |

### 1.3 高風險區

| 風險 | 策略 |
|------|------|
| LLM 幻觉产品（N-05） | conf gate 0.5/0.3 边界；无官网不脑补 |
| 同公司并发 ingest | idempotency_key + dedupe integration |
| reject 后 re-enrich 自动复活（DDR-32） | reject + 完成 enrich → UI仍 rejected |
| M3 pass 2 未触发（DDR-31） | conf 0.72 mock → inference pass 2 job 断言 |
| 跨用户 company 泄露 | 全 API 404/403 |
| SSRF via website fetch | private IP / metadata URL block |
| Free quota 绕过 | 第 4 次 manual 403；daily limit 429 |
| 列表 N+1 | batch enrichment query 性能断言（P1） |

### 1.4 Mock / Fixture 策略

| 資源 | 路徑 | 用途 |
|------|------|------|
| 官網 HTML | `fixtures/websites/abc-tech-home.html` | 正常 enrich |
| 空内容页 | `fixtures/websites/empty-about.html` | partial/failed |
| LLM mock | `__mocks__/enrichment-llm.ts` | conf 0.45 / 0.72 / 0.85 |
| Event payload | `fixtures/events/company-enrich-requested.json` | M3→M6 契約 |
| Entitlement seed | test helper `seedFreeUser()` / `seedProUser()` | 配額測試 |

### 1.5 Definition of Done（QA 签 off）

- [ ] P0 案例 100% Pass
- [ ] E2E smoke：ingest → enrich → 详情 products 绿
- [ ] conf 边界 0.49/0.50/0.51 全 Pass
- [ ] M3 pass 2 联测 Pass
- [ ] 无 P0/P1 open bugs
- [ ] axe-core：enrichment 区块 0 critical

---

## 2. 測試案例 — P0

### 2.1 背景 Enrich 触发（US-6.1 / F-6.5）

#### TC-M6-001 | Contact 建立后 enrich job 入队
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | M3 upsert；company_name 有值 |
| **Steps** | 1. 消费 ContactUpsert<br>2. 查 enrich_jobs / BullMQ |
| **Expected** | 60s 内 `CompanyEnrichRequested` 消费；enrich_status=pending |

#### TC-M6-002 | 无 company_name 不触发 enrich
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | handoff company_name 空 |
| **Expected** | 无 enrich job；详情无 AI 补全区 |

#### TC-M6-003 | 官网可达 → products 写入
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | HTML fixture + LLM mock conf=0.78 |
| **Expected** | company_enrichments.main_products 非空；enrich_status=completed |

#### TC-M6-004 | 无官网 → failed 不脑补
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | discovery 全失败；无 OCR website |
| **Expected** | enrich_status=failed；main_products=[]；不 emit CompanyEnriched |

#### TC-M6-005 | enrich 不阻塞 Contact 可见
| **Priority** | P0 |
| **Type** | E2E |
| **Steps** | M2 收錄 → 立刻打开 /contacts |
| **Expected** | Contact 已出现；enrich pending 不影响列表/详情其他区块 |

---

### 2.2 Company 去重与共享（DDR-30 / F-6.7）

#### TC-M6-006 | 同公司名两 Contact 共享 company_id
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | 两 Contact company_name="ABC Tech"（大小写/后缀略异） |
| **Expected** | 同一 companies.id；enrich 仅一次 fetch（24h 内） |

#### TC-M6-007 | normalize 去重键
| **Priority** | P0 |
| **Type** | Unit |
| **Steps** | `ABC Technology Co., Ltd` vs `abc technology` |
| **Expected** | normalized_name 相同 → upsert 不新建 |

#### TC-M6-008 | 24h dedupe ingest
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | 同 company 1h 内第二笔 ingest |
| **Expected** | 第二 job status=skipped；无重复 HTTP fetch |

#### TC-M6-009 | manual 绕过 24h dedupe
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | ingest 完成 1h 内 POST manual enrich |
| **Expected** | 新 enrich job 执行；enrich_version++ |

---

### 2.3 Confidence Gate（DDR-29 / DDR-31）

#### TC-M6-010 | conf ≥ 0.5 显示 products + emit event
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | LLM mock conf=0.72 |
| **Expected** | section status=completed；CompanyEnriched queued |

#### TC-M6-011 | conf 0.3–0.49 → partial 不 emit
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | LLM mock conf=0.45 |
| **Expected** | enrich_status=partial；无 CompanyEnriched；详情 InsufficientBlock |

#### TC-M6-012 | conf < 0.3 → failed
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | LLM mock conf=0.25 |
| **Expected** | status=failed；列表不显示 products preview |

#### TC-M6-013 | 边界 conf=0.50 显示
| **Priority** | P0 |
| **Type** | Unit |
| **Preconditions** | SectionBuilder conf=0.50 |
| **Expected** | show_products=true；emit 条件满足 |

#### TC-M6-014 | 边界 conf=0.49 不显示
| **Priority** | P0 |
| **Type** | Unit |
| **Preconditions** | SectionBuilder conf=0.49 |
| **Expected** | status=partial；列表 preview hidden |

---

### 2.4 名片库列表预览（US-6.3）

#### TC-M6-015 | 列表显示 company_products_preview
| **Priority** | P0 |
| **Type** | E2E |
| **Preconditions** | enrich completed conf≥0.5；无 responsibility 摘要 |
| **Expected** | AI 摘要列显示「工業電腦、嵌入式…」 |

#### TC-M6-016 | 列表优先 responsibility 摘要
| **Priority** | P0 |
| **Type** | Component |
| **Preconditions** | responsibility conf=0.67 + products 有值 |
| **Expected** | 摘要列显示推估文案；非 products |

#### TC-M6-017 | enrich pending 列表 shimmer
| **Priority** | P0 |
| **Type** | Component |
| **Preconditions** | enrich_status=pending |
| **Expected** | 「⏳ 補全公司資訊中…」；非空白占位 |

#### TC-M6-018 | failed/partial 列表不显示 products
| **Priority** | P0 |
| **Type** | Component |
| **Preconditions** | enrich failed 或 conf<0.5 |
| **Expected** | CompanyProductsPreview render null |

---

### 2.5 详情 AI 补全区（UI/UX §2.2）

#### TC-M6-019 | pending 状态 UI
| **Priority** | P0 |
| **Type** | Component |
| **Expected** | 「⏳ 正在補充公司資訊…」；aria-busy=true |

#### TC-M6-020 | completed 完整显示
| **Priority** | P0 |
| **Type** | E2E |
| **Expected** | products 列表 + ProvenanceBadge + 「更新於 YYYY-MM-DD」 |

#### TC-M6-021 | partial 資訊不足 UI
| **Priority** | P0 |
| **Type** | Component |
| **Expected** | 「資訊不足，建議確認公司名稱」+ [編輯公司名稱] |

#### TC-M6-022 | failed 不影响名片原文
| **Priority** | P0 |
| **Type** | E2E |
| **Expected** | 「⚠️ 無法取得公司公開資訊」；OCR 字段仍可见可复制 |

#### TC-M6-023 | enriched_at 显示（DDR-35）
| **Priority** | P0 |
| **Type** | Component |
| **Expected** | caption「更新於 {date}」与 last_enriched_at 一致 |

---

### 2.6 M3 整合 — pass 2 + index（US-6.4）

#### TC-M6-024 | CompanyEnriched 触发 pass 2
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | enrich completed；products 非空 conf≥0.5 |
| **Expected** | responsibility-inference job pass=2 queued |

#### TC-M6-025 | partial 不触发 pass 2
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | conf=0.45 partial |
| **Expected** | 无 pass 2 job |

#### TC-M6-026 | enrich 后 re-index 含 company_products
| **Priority** | P0 |
| **Type** | Integration |
| **Expected** | contact_search_documents.search_text 含 products 字符串 |

#### TC-M6-027 | company_name 变更 re-trigger enrich
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | PATCH contact company_name |
| **Expected** | 新 CompanyEnrichRequested；trigger=company_name_changed |

---

### 2.7 安全与隔离

#### TC-M6-028 | 跨用户 GET /companies/:id → 404
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | User B 访问 User A 的 companyId |
| **Expected** | 404 COMPANY_NOT_FOUND |

#### TC-M6-029 | SSRF private IP blocked
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | OCR website=http://127.0.0.1 |
| **Expected** | fetch 拒绝；enrich failed NO_WEBSITE |

#### TC-M6-030 | robots.txt Disallow 尊重（B-10）
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | fixture robots Disallow / |
| **Expected** | 不抓取；failed 或 partial（依 ENG 实现） |

---

### 2.8 E2E 冒烟

#### TC-M6-031 | 收錄 → enrich → 详情看懂公司
| **Priority** | P0 |
| **Type** | E2E |
| **Steps** | 1. 收錄名片（mock OCR 含公司名）<br>2. 等 enrich mock 完成<br>3. 打开详情 |
| **Expected** | AI 补全区显示主要产品；pass 2 可选更新推估 |

#### TC-M6-032 | 详情 polling pending→completed
| **Priority** | P0 |
| **Type** | E2E |
| **Preconditions** | enrich 延迟 5s mock |
| **Expected** | 先 pending；60s 内自动变 completed；最多 poll 12 次 |

---

## 3. 測試案例 — P1

### 3.1 审核 — reject / override / re-enrich（US-6.2 / DDR-32）

#### TC-M6-033 | reject 隐藏 products
| **Priority** | P1 |
| **Type** | E2E |
| **Steps** | PATCH review rejected |
| **Expected** | 详情 RejectedBlock；列表 preview 隐藏 |

#### TC-M6-034 | reject 后 enrich 完成不复活
| **Priority** | P1 |
| **Type** | Integration |
| **Steps** | reject → 背景 stale re-enrich 完成 |
| **Expected** | UI 仍 rejected；无 CompanyEnriched emit |

#### TC-M6-035 | re-enrich 恢复
| **Priority** | P1 |
| **Type** | E2E |
| **Steps** | POST re-enrich → 完成 |
| **Expected** | reject 清除；products 再显示 |

#### TC-M6-036 | user_override 显示已修正
| **Priority** | P1 |
| **Type** | Component |
| **Steps** | PATCH override_value |
| **Expected** | 显示 user 值 + 「已修正」badge |

#### TC-M6-037 | accept needs_review
| **Priority** | P1 |
| **Type** | E2E |
| **Preconditions** | needs_review=true conf=0.52 |
| **Steps** | 点「確認正確」 |
| **Expected** | warning badge 变正常；review_status=accepted |

---

### 3.2 手動更新与配额（US-6.6 / DDR-37）

#### TC-M6-038 | manual refresh 成功
| **Priority** | P1 |
| **Type** | E2E |
| **Steps** | 点「更新公司資訊」 |
| **Expected** | 202 + pending → completed Toast |

#### TC-M6-039 | Free 月度配额 3 次
| **Priority** | P1 |
| **Type** | Integration |
| **Steps** | 第 1–3 次 POST enrich 成功 |
| **Expected** | quota_remaining 递减 |

#### TC-M6-040 | Free 第 4 次 403
| **Priority** | P1 |
| **Type** | Integration |
| **Expected** | QUOTA_EXCEEDED；QuotaDialog 显示 |

#### TC-M6-041 | 进行中双击 409
| **Priority** | P1 |
| **Type** | Integration |
| **Steps** | enrich pending 时再 POST |
| **Expected** | ALREADY_IN_PROGRESS；Toast「已在更新中」 |

#### TC-M6-042 | daily enrich quota 429
| **Priority** | P1 |
| **Type** | Integration |
| **Preconditions** | daily_enrich_used=50 |
| **Expected** | DAILY_LIMIT；job delayed |

---

### 3.3 Pro 自动更新（US-6.5 / P1 stub）

#### TC-M6-043 | Free 设置页 Pro 预览
| **Priority** | P1 |
| **Type** | E2E |
| **Steps** | 打开 /settings/company-data |
| **Expected** | Pro 功能预览 + 升级 CTA；无 toggle |

#### TC-M6-044 | Pro auto_refresh 开关
| **Priority** | P1 |
| **Type** | Integration |
| **Preconditions** | seedProUser；auto_refresh_enabled=true |
| **Steps** | stale scan cron |
| **Expected** | 过期 company enqueue stale_auto job |

#### TC-M6-045 | Pro 降级停止 stale
| **Priority** | P1 |
| **Type** | Integration |
| **Steps** | plan_tier 改 free |
| **Expected** | stale scan 0 jobs；既有 cache 保留 |

#### TC-M6-046 | interval 30/60/90 生效
| **Priority** | P1 |
| **Type** | Integration |
| **Preconditions** | interval=30；last_enriched_at 31 days ago |
| **Expected** | 纳入 stale batch |

---

### 3.4 Provenance 与其他 P1

#### TC-M6-047 | Provenance Sheet 来源链接
| **Priority** | P1 |
| **Type** | E2E |
| **Steps** | 点 badge [來源] |
| **Expected** | Sheet 列出 source_urls；外开新分页 |

#### TC-M6-048 | 多候选 needs_review UI
| **Priority** | P1 |
| **Type** | Component |
| **Preconditions** | needs_review=true |
| **Expected** | warning badge「不確定」+ 確認/不準確按钮 |

---

## 4. 邊界 / 錯誤 / 空狀態

| ID | 情境 | Expected |
|----|------|----------|
| TC-M6-E01 | 0 products 可显示 | 列表无 AI 列；详情 partial/failed |
| TC-M6-E02 | enrich 超时 >60s polling | 停止 poll；仍 pending 或 failed 文案 |
| TC-M6-E03 | LLM API 5xx | retry 2x → failed；Contact 正常 |
| TC-M6-E04 | HTTP 403 官网 | retry 1x → failed |
| TC-M6-E05 | 网络离线点 refresh | Toast 错误 + retry |
| TC-M6-E06 | override 空数组 submit | 前端 validation 阻止 |
| TC-M6-E07 | company 无 contact 关联 | GET detail section hidden |
| TC-M6-E08 | Pro 用户 manual 无限 | 不显示「本月剩餘」 |

---

## 5. 無障礙測試

| ID | 檢查項 | Expected |
|----|--------|----------|
| TC-M6-A01 | CompanyEnrichmentBlock region | aria-labelledby 读出「AI 補全 · 公司資訊」 |
| TC-M6-A02 | pending | aria-busy + aria-live polite |
| TC-M6-A03 | completed | aria-label 含产品与信心百分比 |
| TC-M6-A04 | 官网链接 | aria-label 含「新分頁」 |
| TC-M6-A05 | Reject Dialog | focus trap |
| TC-M6-A06 | 配額 caption | 更新后 screen reader 朗读剩余次数 |
| TC-M6-A07 | warning 态 | 不仅靠色彩（icon + 文字） |

---

## 6. 自動化對照

| 測試 ID | 自動化 | CI |
|---------|--------|-----|
| TC-M6-001~004, 006~009 | Vitest integration | every PR |
| TC-M6-007, 010~014 | Vitest unit | every PR |
| TC-M6-015~023 | Testing Library | every PR |
| TC-M6-024~027 | Vitest integration | every PR |
| TC-M6-028~030 | Vitest security | every PR |
| TC-M6-031~032 | Playwright | every PR |
| TC-M6-033~041 | Playwright / Vitest | every PR |
| TC-M6-043~048 | Playwright P1 | nightly |
| TC-M6-A01~07 | axe-core | every PR |

---

## 7. 驗收清單（M6 Release Gate）

### 功能 P0
- [ ] TC-M6-001 ~ 032 全 Pass
- [ ] conf 边界 TC-M6-013~014 Pass
- [ ] 列表/详情状态 TC-M6-015~023 Pass
- [ ] M3 整合 TC-M6-024~027 Pass

### 功能 P1
- [ ] reject/re-enrich TC-M6-033~035 Pass
- [ ] manual quota TC-M6-038~041 Pass
- [ ] Pro settings stub TC-M6-043~044 Pass

### 集成
- [ ] M3 CompanyEnrichRequested 契約测试 Pass
- [ ] M3 CompanyEnriched → pass 2 联测 Pass
- [ ] index company_products 写入 Pass

### 安全
- [ ] TC-M6-028~030 Pass

### 无障碍
- [ ] axe 0 critical on enrichment 区块

### 性能（P1）
- [ ] enrich P95 < 30s（mock 环境 SLA 断言）
- [ ] 列表 50 contacts batch enrichment 无 N+1（query count 断言）

---

## 8. Coupling 回歸

| 模組 | 回歸場景 | 負責 |
|------|---------|------|
| M3 | handoff emit enrich；detail section | M3+M6 联测 |
| M3 | pass 2 inference 输入含 products | M6-024 |
| M3 | 列表 company_products_preview | M6-015 |
| M5 | search_document company_products | M5 QA |
| M5 | query_adopt → enrich | M5+M6 P1 |
| M1 | entitlement seed / Pro toggle | M1 QA |
| M2 | 收錄 → 全链 E2E | M2+M3+M6 |

---

## 9. User Story 覆蓋矩陣

| User Story | 測試案例 |
|------------|---------|
| US-6.1 主要产品自动补全 | TC-M6-001, 003, 010, 031 |
| US-6.2 接受/拒绝/覆写 | TC-M6-033~037, 047 |
| US-6.3 列表看懂公司 | TC-M6-015~018 |
| US-6.4 pass 2 触发 | TC-M6-024~026 |
| US-6.5 Pro 自动更新 | TC-M6-043~046 |
| US-6.6 手动更新配额 | TC-M6-038~042 |

---

## 10. Bug Report 模板

沿用 `BSChat_QA_M2.md` §8 模板；**Module** 填 `M6 公司資訊補全`。

**M6 Severity 補充**：
- **P0**：脑补错误 products、conf<0.5 仍显示、reject 自动复活、pass 2 未触发、跨用户泄露、SSRF
- **P1**：配额错误、polling 破版、Provenance 缺失、stale cron 误跑
- **P2**：needs_review 消歧 UI、Pro 付费页、stats API

---

## 11. M6 LOCKED 條件

| 角色 | 狀態 |
|------|------|
| PM L3 | ✅ v1.1 |
| SA/SD L4 | ✅ v1.0 |
| UI/UX | ✅ v1.0 |
| ENG | ✅ v1.0 |
| QA | ✅ v1.0 |

**🔒 M6 規格 LOCKED** — 可進入實作垂直切片（M2→M3→M6→M5）

---

*QA M6 v1.0 — SDLC Phase 1*
