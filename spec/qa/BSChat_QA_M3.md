# BSChat QA — Module 3：聯絡人結構化與審核

> **依據**：M3 PM L3、M3 SA/SD L4、M3 UI/UX、ENG M3、PRD v2 DDR-7/8/9/21~24  
> **測試框架**：Vitest · Testing Library · Playwright  
> **M3 估算**：P0 案例 26 条 · P1 案例 14 条

---

## 1. 測試策略

### 1.1 測試目標

| 目標 | 說明 |
|------|------|
| **自動建檔** | M2 handoff 後 Contact 自動出現在名片庫 |
| **看懂联系人** | 詳情三區塊；AI 推估仅 conf≥0.6 显示 |
| **宁缺勿滥** | conf<0.6 不写入、UI 不渲染推估区 |
| **Provenance** | OCR 原文 vs AI 推估 vs 人工修正可区分 |
| **可搜索** | index job 写入 `contact_search_documents` |
| **隔离** | 用户只能访问自己的 Contact |
| **删除完整** | soft-delete + cascade M2 raw_card |

### 1.2 測試金字塔（M3）

```
        ┌─────────┐
        │ E2E  6  │  handoff→列表→详情→reject/delete
        ├─────────┤
        │ Int  14 │  upsert worker, inference gate, index, API
        ├─────────┤
        │ Unit 18 │  display resolver, confidence gate, index builder
        └─────────┘
```

### 1.3 高風險區

| 風險 | 策略 |
|------|------|
| M2→M3 handoff 契约漂移 | fixture payload 契约测试 |
| Inference 常错（DDR-9） | mock conf 边界 0.59/0.60/0.61 |
| conf<0.6 仍显示 UI | component 断言 ResponsibilityBlock absent |
| 重复 handoff 重复 Contact | raw_card_id idempotency integration |
| 跨用户数据泄露 | 全 API 403/404 测试 |
| Index 与 Contact 不一致 | index job 后 search_document 断言 |
| M6 未就绪详情破版 | pending 状态 UI snapshot |

### 1.4 Definition of Done（QA 签 off）

- [ ] P0 案例 100% Pass
- [ ] E2E smoke：handoff → 列表 → 详情 绿
- [ ] inference gate 边界测试 Pass
- [ ] 无 P0/P1 open bugs
- [ ] axe-core：/contacts, /contacts/[id] 0 critical

---

## 2. 測試案例 — P0

### 2.1 Handoff 自动建档（US-3.1）

#### TC-M3-001 | M2 handoff 后 Contact 自动创建
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | M2 OCR 完成；ContactUpsertRequested emitted |
| **Steps** | 1. Worker 消费 handoff<br>2. GET /contacts |
| **Expected** | 30s 内列表出现新 Contact；display_name/company/title 正确 |

#### TC-M3-002 | 重复 handoff 不重复创建
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | 同 raw_card_id handoff 2 次 |
| **Expected** | contacts 表仅 1 行；第二次 UPDATE；version++ |

#### TC-M3-003 | 缺 name 仍创建
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | handoff fields.name 为空 |
| **Expected** | Contact 创建；display_name=「未命名联系人」或等价；列表可見 |

#### TC-M3-004 | Provenance 逐字段写入
| **Priority** | P0 |
| **Type** | Integration |
| **Expected** | contact_field_provenance 含 name/company/title/phone/email；source=ocr |

---

### 2.2 名片库列表（US-3.3）

#### TC-M3-005 | 列表显示基本字段
| **Priority** | P0 |
| **Type** | E2E |
| **Steps** | 打开 /contacts |
| **Expected** | 每项显示：姓名、公司、抬頭、来源标签 |

#### TC-M3-006 | unconfirmed badge 显示
| **Priority** | P0 |
| **Type** | Component |
| **Preconditions** | review_status=unconfirmed |
| **Expected** | 橘色「未確認」badge |

#### TC-M3-007 | 列表空状态
| **Priority** | P0 |
| **Type** | E2E |
| **Preconditions** | 0 contacts |
| **Expected** | 「還沒有聯絡人」+ CTA「開始收錄名片」→ /capture |

#### TC-M3-008 | 分页加载
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | >20 contacts |
| **Expected** | page=1 limit=20；滚动/load more 正确 |

---

### 2.3 详情三区块（US-3.2 / US-3.4 / DDR-27）

#### TC-M3-009 | 名片原文区永远显示
| **Priority** | P0 |
| **Type** | Component |
| **Expected** | ContactDetailSection variant=original 含 OCR 字段；白底 |

#### TC-M3-010 | AI 推估区 conf≥0.6 显示
| **Priority** | P0 |
| **Type** | Integration + Component |
| **Preconditions** | mock inference confidence=0.72 |
| **Expected** | ResponsibilityBlock 可见；ProvenanceBadge「AI 推估 · 72%」；淡蓝底 |

#### TC-M3-011 | AI 推估区 conf<0.6 不显示
| **Priority** | P0 |
| **Type** | Integration + Component |
| **Preconditions** | mock inference confidence=0.55 |
| **Expected** | contacts.responsibility_scope=NULL；UI **无** ResponsibilityBlock；**无**空白占位 |

#### TC-M3-012 | 信心边界 0.60
| **Priority** | P0 |
| **Type** | Unit |
| **Steps** | threshold=0.6；输入 0.59 / 0.60 / 0.61 |
| **Expected** | 0.59 不写入；0.60 写入；0.61 写入 |

#### TC-M3-013 | M6 未就绪显示 pending
| **Priority** | P0 |
| **Type** | Component |
| **Preconditions** | company_enrichment=null |
| **Expected** | CompanyEnrichmentBlock「正在補充公司資訊...」或整区 pending |

#### TC-M3-014 | 来源与隐私信息
| **Priority** | P0 |
| **Type** | E2E |
| **Expected** | 详情底部：source_label、🔒 私人、收录日期 |

---

### 2.4 职责推断 Worker（DDR-21）

#### TC-M3-015 | Pass 1 创建后触发
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | handoff 完成 |
| **Expected** | responsibility-inference job pass=1 enqueued |

#### TC-M3-016 | Pass 2 M6 enrich 后 supersede
| **Priority** | P1 |
| **Type** | Integration |
| **Preconditions** | pass1 conf=0.65；CompanyEnriched with products |
| **Expected** | pass2 conf 更高 → 旧 inference status=superseded；UI 显示新 scope |

#### TC-M3-017 | Inference API 失败
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | mock Claude 3x fail |
| **Expected** | Contact 仍 ACTIVE；无 responsibility_scope；详情无 AI 推估区 |

---

### 2.5 搜索索引（DDR-25）

#### TC-M3-018 | Index job 写入 search_document
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | Contact 创建 → index worker |
| **Expected** | contact_search_documents 有 row；search_status=indexed |

#### TC-M3-019 | 推估更新后 re-index
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | inference 写入 scope → index job |
| **Expected** | search_text 含 responsibility_scope；content_hash 更新 |

#### TC-M3-020 | unconfirmed 仍 indexed
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | review_status=unconfirmed |
| **Expected** | search_document 存在（M5 可搜；M3 不负责排序权重）

---

### 2.6 删除（R-7）

#### TC-M3-021 | 删除 Contact soft-delete
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | DELETE /contacts/:id |
| **Expected** | deleted_at 设置；GET 404 |

#### TC-M3-022 | 删除 emit DeleteCardCascade
| **Priority** | P0 |
| **Type** | Integration |
| **Expected** | queue 收到 `{ raw_card_id }`；M2 raw_card 后续删除 |

#### TC-M3-023 | 删除确认 Dialog
| **Priority** | P0 |
| **Type** | E2E |
| **Expected** | Dialog 文案含「一併刪除名片原圖」；确认后返回列表 |

---

### 2.7 授权与安全

#### TC-M3-024 | 未登录 401
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | 无 JWT GET /contacts |
| **Expected** | 401 |

#### TC-M3-025 | 跨用户访问 404
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | User A 访问 User B 的 contact id |
| **Expected** | 404（不泄露存在性） |

#### TC-M3-026 | M2 re-handoff 更新 Contact
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | M2 review 修改 company → re-handoff |
| **Expected** | Contact company 更新；provenance 更新；re-enrich event（stub 断言） |

---

## 3. 測試案例 — P1

### 3.1 Reject 推估（US-3.2 negative）

#### TC-M3-027 | Reject inference 隐藏区块
| **Priority** | P1 |
| **Type** | E2E |
| **Steps** | 详情点「不準？」→ 确认隐藏 |
| **Expected** | POST reject-inference；ResponsibilityBlock 消失；不 prompt 手动填写 |

#### TC-M3-028 | Reject 后 re-index
| **Priority** | P1 |
| **Type** | Integration |
| **Expected** | search_text 不含旧 responsibility_scope |

---

### 3.2 事后编辑（US-3.5）

#### TC-M3-029 | PATCH 更新字段
| **Priority** | P1 |
| **Type** | Integration |
| **Steps** | PATCH company_name + version |
| **Expected** | manual_overrides 写入；provenance source=manual；显示「已修正」 |

#### TC-M3-030 | PATCH 409 version conflict
| **Priority** | P1 |
| **Type** | Integration |
| **Expected** | 409；UI Toast 刷新 |

#### TC-M3-031 | 修改 company 触发 re-enrich
| **Priority** | P1 |
| **Type** | Integration |
| **Expected** | CompanyEnrichRequested emitted |

---

### 3.3 列表筛选与复制（M8 stub）

#### TC-M3-032 | 筛选 unconfirmed
| **Priority** | P1 |
| **Type** | E2E |
| **Expected** | 仅显示 unconfirmed 联系人 |

#### TC-M3-033 | 复制电话 Toast
| **Priority** | P1 |
| **Type** | E2E |
| **Expected** | 点复制 →「已複製」；clipboard 正确 |

---

### 3.4 UI/UX 回归

#### TC-M3-034 | AI 区与原文区视觉区分
| **Priority** | P1 |
| **Type** | Visual/Manual |
| **Expected** | original=白底；ai-inferred=--color-ai-bg |

#### TC-M3-035 | 低信心 OCR dot
| **Priority** | P1 |
| **Type** | Component |
| **Preconditions** | title confidence=0.65 |
| **Expected** | 🟠 dot + 非仅依赖颜色（有文字） |

#### TC-M3-036 | 桌面 split view
| **Priority** | P1 |
| **Type** | E2E |
| **Viewport** | ≥1024px |
| **Expected** | 左列表右详情；选中同步 |

---

### 3.5 M2 集成回归

#### TC-M3-037 | E2E：收录→名片库出现
| **Priority** | P0 |
| **Type** | E2E |
| **Steps** | 连拍 1 张 → 等 OCR → 打开 /contacts |
| **Expected** | 新 Contact 可见；可进详情 |

#### TC-M3-038 | 待确认不影响名片库显示
| **Priority** | P0 |
| **Type** | E2E |
| **Preconditions** | pending_review 未确认 |
| **Expected** | 名片库仍显示；badge「未確認」 |

---

### 3.6 性能

#### TC-M3-039 | 列表 API P95 <500ms
| **Priority** | P1 |
| **Type** | Load |
| **Preconditions** | 100 contacts |
| **Expected** | GET /contacts P95 <500ms |

#### TC-M3-040 | 详情 API P95 <300ms
| **Priority** | P1 |
| **Type** | Load |
| **Expected** | GET /contacts/:id P95 <300ms |

---

## 4. 空状态测试

| ID | 位置 | 条件 | Expected |
|----|------|------|----------|
| TC-M3-E01 | /contacts | 0 rows | 空状态 + 收录 CTA |
| TC-M3-E02 | 详情 AI 推估 | conf<0.6 | **区块不渲染** |
| TC-M3-E03 | 详情 M6 | enrich pending | spinner 文案 |
| TC-M3-E04 | 详情 M6 | enrich failed | 警告+不影响其他 |
| TC-M3-E05 | 筛选 | 0 match | 「沒有符合的聯絡人」 |

---

## 5. 无障碍测试

| ID | 检查项 | Expected |
|----|--------|----------|
| TC-M3-A01 | 三区块 section labels | screen reader 读出「名片原文」「AI 推估」 |
| TC-M3-A02 | ProvenanceBadge | aria-label 含信心百分比 |
| TC-M3-A03 | 复制按钮 | aria-label「複製電話…」 |
| TC-M3-A04 | 删除 Dialog | focus trap |
| TC-M3-A05 | 列表 | role=list/listitem |

---

## 6. 自动化对照

| 测试 ID | 自动化 | CI |
|---------|--------|-----|
| TC-M3-001~004 | Vitest integration | every PR |
| TC-M3-010~012 | Vitest unit | every PR |
| TC-M3-005, 007, 037 | Playwright | every PR |
| TC-M3-021~025 | Vitest integration | every PR |
| TC-M3-027, 029 | Playwright | nightly |
| TC-M3-A01~05 | axe-core | every PR |

---

## 7. 验收清单（M3 Release Gate）

### 功能
- [ ] TC-M3-001 ~ 026 P0 全 Pass
- [ ] TC-M3-037 E2E 收录→名片库 Pass
- [ ] conf 边界 TC-M3-012 Pass
- [ ] 三区块 TC-M3-009~011 Pass

### 集成
- [ ] M2 handoff 契约测试 Pass
- [ ] DeleteCardCascade job 断言 Pass
- [ ] index document 写入 Pass

### 安全
- [ ] TC-M3-024~025 Pass

### 无障碍
- [ ] axe 0 critical on contacts pages

---

## 8. Coupling 回归（M3 LOCKED 后）

| 模块 | 回归场景 | 负责 QA |
|------|---------|---------|
| M2 | handoff payload 变更 | M2+M3 联测 |
| M5 | search_document 消费 | M5 QA |
| M6 | CompanyEnriched → pass2 | M6 QA |
| M8 | 复制/致電按钮 | M8 QA |

---

## 9. Bug Report 模板

沿用 `BSChat_QA_M2.md` §8 模板；**Module** 填 `M3 聯絡人結構化`。

**M3 Severity 补充**：
- **P0**：handoff 失败无 Contact、conf<0.6 仍显示推估、跨用户泄露、删除未 cascade
- **P1**：reject 流程 broken、index 未写入、pending UI 破版
- **P2**：筛选、编辑、桌面 split

---

*QA M3 v1.0 — SDLC Phase 1*
