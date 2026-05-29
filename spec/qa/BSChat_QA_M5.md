# BSChat QA — Module 5：AI 搜尋（對話式找商機）

> **依據**：M5 PM L3 v1.1、M5 SA/SD v1.0、M5 UI/UX v1.0、ENG M5、PRD v2 S-01/DDR-5~10/51~59  
> **測試框架**：Vitest · Testing Library · Playwright · axe-core  
> **M5 估算**：P0 案例 34 条 · P1 案例 14 条

---

## 1. 測試策略

### 1.1 測試目標

| 目標 | 說明 |
|------|------|
| **Aha Moment** | 首次搜尋 ≥1 结果；10 分钟内可体验（DDR-10） |
| **找商機** | 自然语言 query → 排序 + match_reason（US-5.1/5.2） |
| **宁缺勿滥** | 低 confidence 不作主要匹配理由（DDR-9、R-5/R-6） |
| **空结果不放弃** | NO_MATCH / NO_INDEXED 引导收录换问法（N-02、DDR-55） |
| **不搜他人人脉** | 仅 Pool A；user_id 隔离（DDR-59） |
| **pending 可搜** | unconfirmed 联系人可出现（DDR-22） |
| **降级可用** | LLM 失败仍 tsvector 结果 + degraded |
| **隐私可见** | Privacy Strip；不暴露跨用户数据 |
| **M3/M6 整合** | index 含 products；详情 Context Banner |
| **配额** | cache daily / live monthly（P1） |

### 1.2 測試金字塔（M5）

```
        ┌─────────┐
        │ E2E   8 │  收录→index→搜尋→详情→复制
        ├─────────┤
        │ Int  20 │  retrieval, rerank validate, quota, persist
        ├─────────┤
        │ Unit  20│  buildSearchString, validateRerank, empty builder
        └─────────┘
```

| 層級 | 工具 | M5 覆蓋 |
|------|------|---------|
| Unit | Vitest | `validateRerankItem`, `buildEmptyState`, `buildSearchString` |
| Integration | Vitest + test DB | retrieval SQL, POST /search/queries, quota |
| Component | Testing Library | `SearchResultCard`, `SearchEmptyState`, `AhaMomentModal` |
| E2E | Playwright + LLM mock | 搜尋 Tab happy path、empty、Aha |
| Manual | 清單 | 10 条真实 TW B2B 自然语言 query 抽测 |

### 1.3 高風險區

| 風險 | 策略 |
|------|------|
| LLM 幻觉 match_reason（N-05） | validate-rerank + conf 门槛 TC-M5-018~021 |
| 搜到他人私人库（DDR-59） | user_id filter 全路径 TC-M5-028~030 |
| 0 结果导致流失（N-02） | empty UX + 不同 reason TC-M5-011~014 |
| Aha 未触发（DDR-10） | 首次有结果 aha_moment TC-M5-015 |
| products conf<0.5 当主理由 | TC-M5-019 |
| inference conf<0.6 当主理由 | TC-M5-020 |
| LLM 全挂无结果 | degraded fallback TC-M5-022 |
| index 未就绪 | status + NO_INDEXED TC-M5-010 |
| cache quota 绕过 | 第 31 次 429 TC-M5-031 |
| live 写 M6 cache（DDR-36） | P1 adopt 路径断言 TC-M5-040 |

### 1.4 Mock / Fixture 策略

| 資源 | 路徑 | 用途 |
|------|------|------|
| Indexed contacts seed | `fixtures/search/contacts-ipc-seed.ts` | 5 家工业电脑相关 |
| Empty user seed | `fixtures/search/user-zero-index.ts` | NO_INDEXED |
| LLM rerank mock | `__mocks__/search-rerank-llm.ts` | 正常 / 幻觉 / throw |
| LLM intent mock | `__mocks__/search-intent-llm.ts` | products/roles 解析 |
| Search API response | `fixtures/api/search-completed.json` | component 测试 |

**Seed 场景（E2E）**：

| User | indexed | 用途 |
|------|---------|------|
| `user-search-rich` | ≥8，含 IPC enrich | happy path |
| `user-search-empty` | 0 | NO_INDEXED_CONTACTS |
| `user-search-sparse` | 2 | LOW_INDEX_COUNT hint |
| `user-search-nomatch` | 5，无 IPC | NO_MATCH |

### 1.5 Definition of Done（QA 签 off）

- [ ] P0 案例 100% Pass
- [ ] E2E smoke：搜尋「工業電腦」→ ≥1 结果 + match_reason
- [ ] empty 两种 reason UI 区分 Pass
- [ ] Aha 仅一次 Pass
- [ ] 跨用户隔离 Pass
- [ ] 无 P0/P1 open bugs
- [ ] axe-core：搜尋 Tab 0 critical

---

## 2. 測試案例 — P0

### 2.1 Search Status（F-5.7 / US-5.4）

#### TC-M5-001 | GET /search/status 返回 indexed_count
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | user 有 5 笔 indexed |
| **Expected** | `indexed_count=5`, `can_search=true`, `sample_queries=[]`（MVP / DDR-71） |

#### TC-M5-002 | 0 indexed → can_search false
| **Priority** | P0 |
| **Type** | Integration |
| **Expected** | `indexed_count=0`, `can_search=false` |

#### TC-M5-003 | 搜尋 Tab 不顯示通用靈感 chips（DDR-71）
| **Priority** | P0 |
| **Type** | Component |
| **Steps** | mount SearchPage with status mock |
| **Expected** | 無範例 pill；textarea placeholder 為中性文案；僅「搜尋」Primary 按鈕 |

#### TC-M5-004 | indexed < 3 仍显示输入框
| **Priority** | P0 |
| **Type** | E2E |
| **Preconditions** | user-search-sparse |
| **Expected** | 输入框未 disabled；caption「再多收幾張」 |

---

### 2.2 对话式搜尋（US-5.1 / F-5.1~5.2）

#### TC-M5-005 | 自然语言 query 返回 COMPLETED
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | user-search-rich；LLM rerank mock 正常 |
| **Steps** | POST `{ query_text: "我手上有誰做工業電腦的？" }` |
| **Expected** | status=COMPLETED；results.length ≥ 1；每项含 match_reason |

#### TC-M5-006 | 无需 profile 即可搜（DDR-5）
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | 连续两次不同意图 query |
| **Expected** | 均 200；无 profile 字段读写 |

#### TC-M5-007 | query 过长 → 400
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | query_text > 2000 chars |
| **Expected** | `QUERY_TOO_LONG` 400 |

#### TC-M5-008 | 空 query → 400
| **Priority** | P0 |
| **Type** | Integration |
| **Expected** | validation error |

#### TC-M5-009 | 结果含 contact_preview
| **Priority** | P0 |
| **Type** | Integration |
| **Expected** | display_name, company_name, title, phones, emails  populated |

---

### 2.3 空结果（US-5.3 / F-5.5 / DDR-55）

#### TC-M5-010 | NO_INDEXED_CONTACTS
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | user-search-empty |
| **Expected** | status=EMPTY；`empty_state.reason=NO_INDEXED_CONTACTS`；cta.action=capture |

#### TC-M5-011 | NO_MATCH
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | user-search-nomatch |
| **Steps** | query「量子計算」 |
| **Expected** | status=EMPTY；reason=NO_MATCH；`sample_queries=[]`（MVP） |

#### TC-M5-012 | NO_INDEXED UI CTA
| **Priority** | P0 |
| **Type** | E2E |
| **Expected** | 「開始收錄」→ navigate /capture |

#### TC-M5-013 | NO_MATCH UI 换问法
| **Priority** | P0 |
| **Type** | Component |
| **Expected** | SearchEmptyState 显示 `suggestions` 引導文案；无通用範例 chip；无责备文案 |

#### TC-M5-013b | Pro 個人化搜尋建議（P1 / DDR-71）
| **Priority** | P1 |
| **Type** | Component |
| **Preconditions** | seedProUser；status.sample_queries 非空（依索引推導） |
| **Expected** | 1–3 個 pill 顯示；點擊只填入輸入框、不自動 POST；文案與使用者名片池相關 |

#### TC-M5-013c | 硬條件不滿足則排除（DDR-73）
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | 索引含 AWS/Amazon 聯絡人 A（PM）與 B（Solutions Architect） |
| **Steps** | query「AWS 人脈中找架構師就好」 |
| **Expected** | 僅 B 在 results；A 不得出現；若無 B 則 NO_MATCH；不得出現「不符合但仍列出」的 match_reason |

#### TC-M5-014 | LOW_INDEX_COUNT hint
| **Priority** | P0 |
| **Type** | E2E |
| **Preconditions** | user-search-sparse |
| **Expected** | empty 或 status caption 含「再多收幾張」 |

---

### 2.4 Aha Moment（US-5.4 / DDR-10）

#### TC-M5-015 | 首次有结果 → aha_moment true
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | 用户无 prior COMPLETED query |
| **Expected** | response `aha_moment: true` |

#### TC-M5-016 | 第二次 search 不返回 aha
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | 连续两次 COMPLETED search |
| **Expected** | 第二次 `aha_moment: false` |

#### TC-M5-017 | Aha Modal 仅显示一次
| **Priority** | P0 |
| **Type** | E2E |
| **Steps** | 首次 aha → dismiss → 再搜 |
| **Expected** | Modal 不再出现（localStorage） |

---

### 2.5 匹配理由与信心（US-5.2 / DDR-53 / R-5/R-6）

#### TC-M5-018 | match_reason 引用真实字段
| **Priority** | P0 |
| **Type** | Integration |
| **Expected** | 每条 match_sources 对应 candidate 实际值 |

#### TC-M5-019 | products conf < 0.5 不得作 match_source
| **Priority** | P0 |
| **Type** | Unit + Integration |
| **Preconditions** | candidate products_confidence=0.42；LLM 返回 company_products source |
| **Expected** | validate 剔除或降级；最终无 company_products source |

#### TC-M5-020 | inference conf < 0.6 不得作 match_source
| **Priority** | P0 |
| **Type** | Unit + Integration |
| **Preconditions** | responsibility_confidence=0.55 |
| **Expected** | match_sources 无 responsibility_scope |

#### TC-M5-021 | UI 显示「符合原因」区块
| **Priority** | P0 |
| **Type** | Component |
| **Expected** | SearchResultCard 含 match_reason 主区块 |

#### TC-M5-022 | LLM 失败 → degraded + fallback 结果
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | rerank mock throw |
| **Expected** | degraded=true；results.length > 0；简化 match_reason |

---

### 2.6 pending_review 可搜（DDR-22 / F-5.6）

#### TC-M5-023 | unconfirmed 联系人出现在结果
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | contact review_status=unconfirmed；index 存在 |
| **Expected** | 可出现在 results；preview.review_status=unconfirmed |

#### TC-M5-024 | 结果卡显示「未確認」badge
| **Priority** | P0 |
| **Type** | Component |
| **Expected** | badge visible |

---

### 2.7 检索层（Layer A / DDR-63）

#### TC-M5-025 | company_products in search_text 可命中
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | M6 enrich 后 index 含「工業電腦」 |
| **Steps** | query 含「工業電腦」 |
| **Expected** | retrieval candidates ≥ 1 |

#### TC-M5-026 | tsvector 0 hit → pg_trgm fallback
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | company_name 相似但 ts 弱匹配 |
| **Expected** | fallback 仍返回 candidates |

#### TC-M5-027 | confirmed contact rank boost（DDR-56）
| **Priority** | P1 |
| **Type** | Unit |
| **Preconditions** | 两 candidate 分数接近；一 confirmed |
| **Expected** | confirmed 排名靠前 |

---

### 2.8 安全与隔离（DDR-59 / R-2）

#### TC-M5-028 | 仅搜当前 user 的 index
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | user A index 5；user B index 5 |
| **Steps** | user A search |
| **Expected** | 结果 contact_id 均属 user A |

#### TC-M5-029 | GET /search/queries/:id 跨用户 404
| **Priority** | P0 |
| **Type** | Integration |
| **Expected** | 404 |

#### TC-M5-030 | search_scope=network → 403（MVP）
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | POST `{ search_scope: "network" }` |
| **Expected** | `SEARCH_SCOPE_NOT_ALLOWED` 403 |

---

### 2.9 配额（R-10 / PRD §11）

#### TC-M5-031 | cache daily quota 429
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | search_cache_used_today=30 |
| **Expected** | 429 `SEARCH_QUOTA_EXCEEDED` |

#### TC-M5-032 | quota 显示于 status
| **Priority** | P0 |
| **Type** | Integration |
| **Expected** | `quotas.search_cache_remaining_today` 正确 |

---

### 2.10 UI 整合（F-5.4 / F-5.16 / M3/M8）

#### TC-M5-033 | 点击结果 → 详情带 from_search
| **Priority** | P0 |
| **Type** | E2E |
| **Steps** | 点 SearchResultCard |
| **Expected** | URL 含 `from_search=`；SearchContextBanner 可见 |

#### TC-M5-034 | Context Banner 显示 match_reason
| **Priority** | P0 |
| **Type** | Component |
| **Expected** | 全文 + match_sources chips |

#### TC-M5-035 | 复制电话 Toast
| **Priority** | P0 |
| **Type** | E2E |
| **Steps** | 点「複製電話」 |
| **Expected** | Toast「已複製」；clipboard 有值 |

#### TC-M5-036 | Privacy Strip 常显
| **Priority** | P0 |
| **Type** | E2E |
| **Expected** | 搜尋 Tab 顶栏含「預設私人」 |

---

### 2.11 持久化与删除

#### TC-M5-037 | search_queries + search_results 写入
| **Priority** | P0 |
| **Type** | Integration |
| **Expected** | POST 后 DB 有 query row + result rows |

#### TC-M5-038 | 删除 contact 后不再出现
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | search 命中 → delete contact → 再 search |
| **Expected** | 该 contact_id 不在 results |

---

## 3. 測試案例 — P1

### 3.1 Live Augment（US-5.5 / F-5.8~5.10）

#### TC-M5-039 | suggest_live when top1 < 0.45
| **Priority** | P1 |
| **Type** | Integration |
| **Expected** | `suggest_live: true` |

#### TC-M5-040 | live-augment 写 query_augmentations 不写 M6 cache
| **Priority** | P1 |
| **Type** | Integration |
| **Steps** | POST live-augment → worker 完成 |
| **Expected** | query_augmentations 有 row；company_enrichments 无新 version（除非 adopt） |

#### TC-M5-041 | live quota 用尽 403
| **Priority** | P1 |
| **Type** | Integration |
| **Preconditions** | live_augment_used=5 |
| **Expected** | `LIVE_QUOTA_EXCEEDED` |

#### TC-M5-042 | adopt → M6 query_adopt
| **Priority** | P1 |
| **Type** | Integration |
| **Steps** | POST adopt |
| **Expected** | M6 enrich job trigger_type=query_adopt；adopted=true |

#### TC-M5-043 | LiveAugmentBanner UI
| **Priority** | P1 |
| **Type** | Component |
| **Expected** | suggest_live 时 banner + 剩余次数 |

#### TC-M5-044 | 即時查詢 badge 于 match_reason
| **Priority** | P1 |
| **Type** | E2E |
| **Expected** | 「即時查詢」标注可见 |

---

### 3.2 Refinement / Session（F-5.11~5.13）

#### TC-M5-045 | refinement_suggestions 显示
| **Priority** | P1 |
| **Type** | Component |
| **Preconditions** | API 返回 suggestions |
| **Expected** | chips 可点击填入 |

#### TC-M5-046 | 多轮 session 第二 turn
| **Priority** | P1 |
| **Type** | Integration |
| **Steps** | POST session → turn2 |
| **Expected** | session.turn_count=2；context 含 turn1 摘要 |

---

### 3.3 性能与无障碍

#### TC-M5-047 | cache search P95 < 3s（mock LLM）
| **Priority** | P1 |
| **Type** | Integration |
| **Preconditions** | 20 contacts seed |
| **Expected** | latency_ms P95 断言 |

#### TC-M5-048 | axe 搜尋 Tab 0 critical
| **Priority** | P0 |
| **Type** | a11y |
| **Expected** | 0 critical violations |

#### TC-M5-049 | 键盘 Enter 送出 search
| **Priority** | P1 |
| **Type** | E2E |
| **Expected** | Cmd/Ctrl+Enter 触发 POST |

#### TC-M5-050 | SearchResultCard aria
| **Priority** | P1 |
| **Type** | a11y |
| **Expected** | role=article；match_reason aria-label |

---

### 3.4 跨模块回归

#### TC-M5-051 | 收錄完成 invalidate search/status
| **Priority** | P1 |
| **Type** | E2E |
| **Steps** | M2 收錄第 4 张 → 回搜尋 Tab |
| **Expected** | indexed_count 更新 |

#### TC-M5-052 | M6 enrich 后 search 可命中新产品
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | CompanyEnriched → re-index → search |
| **Expected** | match_reason 可含新 products |

---

## 4. E2E 场景脚本

### E2E-M5-001 | Aha 全链（S-01）

```
1. 注册新用户
2. M2 连拍 3 张（mock OCR + index）
3. 默认进入搜尋 Tab
4. 输入「我手上有誰做工業電腦的？」
5. Assert: ≥1 SearchResultCard + match_reason
6. Assert: AhaMomentModal 出现
7. 点「查看結果」→ 详情 Context Banner
8. 复制电话 → Toast
```

### E2E-M5-002 | 空结果不放弃（N-02）

```
1. user-search-nomatch 登录
2. 搜尋「量子計算」
3. Assert: EMPTY + 换问法 + 範例
4. 点「去收錄名片」→ /capture
```

### E2E-M5-003 | Degraded 仍可用

```
1. 设置 rerank mock throw
2. 搜尋
3. Assert: degraded 小字 + results.length > 0
```

---

## 5. 驗收清單（M5 Release Gate）

### 功能 P0
- [ ] TC-M5-001 ~ 038 全 Pass
- [ ] TC-M5-048 axe Pass
- [ ] TC-M5-052 M6 整合 Pass

### 功能 P1
- [ ] TC-M5-039 ~ 047, 049 ~ 051 Pass
- [ ] live/adopt 链 TC-M5-040~042 Pass

### 集成
- [ ] M3 index read 契約 Pass
- [ ] M3 Context Banner Pass
- [ ] M8 copy stub Pass
- [ ] M2→M3→M6→M5 垂直切片 E2E-M5-001 Pass

### 安全
- [ ] TC-M5-028 ~ 030 Pass
- [ ] 不 log 完整 query 到 stdout（代码审查）

### 性能（P1）
- [ ] TC-M5-047 P95 < 3s（20 contacts，mock LLM）

---

## 6. Coupling 回歸

| 模組 | 回歸場景 | 負責 |
|------|---------|------|
| M2 | 收錄 → index → 可搜 | E2E-M5-001 |
| M3 | contact_search_documents；详情 banner | TC-M5-033~034 |
| M3 | pending_review 可索引 | TC-M5-023 |
| M6 | products in index | TC-M5-025, 052 |
| M6 | query_adopt（P1） | TC-M5-042 |
| M8 | 复制 CTA | TC-M5-035 |
| M1 | entitlement quota | TC-M5-031~032 |
| M7 | user-scoped only | TC-M5-028 |

---

## 7. User Story 覆蓋矩陣

| User Story | 測試案例 |
|------------|---------|
| US-5.1 对话式找商機 | TC-M5-005~009, 025~026, E2E-001 |
| US-5.2 搜尋結果解釋 | TC-M5-018~021, 034 |
| US-5.3 空結果不放棄 | TC-M5-010~014, E2E-002 |
| US-5.4 Aha 首次搜尋 | TC-M5-001~004, 015~017, E2E-001 |
| US-5.5 即時深入查詢（P1） | TC-M5-039~044 |
| US-5.6 找到後立刻行動 | TC-M5-035 |

---

## 8. Bug Report 模板

沿用 `BSChat_QA_M2.md` §8 模板；**Module** 填 `M5 AI 搜尋`。

**M5 Severity 補充**：
- **P0**：跨用户结果、幻觉 match_reason 无校验、Aha 未触发、NO_MATCH 无引导、pending 被排除、LLM 挂零结果、quota 绕过
- **P1**：degraded 未提示、live 误写 M6 cache、suggest_live 阈值错误、Context Banner 缺失
- **P2**：桌面 split、搜尋历史、refinement chips 样式

---

## 9. M5 LOCKED 條件

| 角色 | 狀態 |
|------|------|
| PM L3 | ✅ v1.1 |
| SA/SD L4 | ✅ v1.0 |
| UI/UX | ✅ v1.0 |
| ENG | ✅ v1.0 |
| QA | ✅ v1.0 |

**🔒 M5 規格 LOCKED** — 可進入實作垂直切片（M2→M3→M6→**M5**）

**Phase 3（Pool B / M11）**：不在 MVP LOCK 范围；M5b 另开 QA 轮次。

---

## 10. 垂直切片验收顺序（Implementation）

```
1. M3 index seed + GET /search/status
2. POST /search/queries integration（mock LLM）
3. SearchPage + ResultCard UI
4. Empty + Aha E2E
5. Context Banner + copy
6. Quota + security cases
7. P1 live/adopt（可选第二批）
```

---

*QA M5 v1.0 — SDLC Phase 1*
