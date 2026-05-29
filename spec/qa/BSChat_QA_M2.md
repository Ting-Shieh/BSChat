# BSChat QA — Module 2：名片收錄（含 OCR）

> **依據**：M2 PM L3、SA/SD L4、UI/UX M2、ENG M2、PRD v2 S-02/S-03  
> **測試框架**：Vitest（unit）、Testing Library（component）、Playwright（E2E）  
> **M2 估算**：P0 案例 28 条 · P1 案例 12 条

---

## 1. 測試策略

### 1.1 測試目標

| 目標 | 說明 |
|------|------|
| **零摩擦收錄** | 连拍单张 upload 触发 <3s；收錄當下零必填 |
| **資料不丟** | 部分失败不影响其他卡片；OCR 失败保留原图 |
| **最低確認** | 仅姓名/公司/抬頭可编辑（DDR-18） |
| **Aha Moment** | ≥3 张 OCR 完成触发搜索引导 |
| **安全** | 用户只能访问自己的卡片；SSRF/上传攻击防护 |

### 1.2 測試金字塔（M2）

```
        ┌─────────┐
        │ E2E  8  │  Playwright — 关键用户旅程
        ├─────────┤
        │ Int  12 │  API + Worker + DB — supertest / job test
        ├─────────┤
        │ Unit 20 │  validators, review logic, idempotency
        └─────────┘
```

| 層級 | 工具 | M2 覆蓋目標 |
|------|------|------------|
| Unit | Vitest | OCR review status logic, Zod validators, hash dedup |
| Integration | Vitest + test DB | Upload API, OCR worker mock, review 409 |
| Component | Testing Library | ReviewCard, ThumbnailStrip, BurstCapture |
| E2E | Playwright | 连拍→OCR→待确认→Aha modal |
| Manual | 清单 | 真机相机、展场弱网、多语名片 |

### 1.3 高風險區（加強測試）

| 風險 | 原因 | 策略 |
|------|------|------|
| OCR 準確度/延遲 | 核心價值鏈起點 | 多语样本集 20 张 + mock Claude |
| 连拍并发 upload | 展覽高頻 | 10 并发 integration test |
| Idempotency | 弱网 retry 重复 | 同 key 重复 POST 测一次写入 |
| 跨用户数据隔离 | 隐私 P0 | 全 API negative auth tests |
| URL import SSRF | 安全 | 私有 IP / metadata URL blocklist |
| auto_accepted 可搜索 | R-3 产品决策 | handoff event 断言 |

### 1.4 Definition of Done（QA 簽 off）

- [ ] P0 测试案例 100% Pass
- [ ] E2E smoke 3 条 CI 绿
- [ ] 无 P0/P1 open bugs
- [ ] 真机连拍 smoke（iOS Safari + Android Chrome 各 1）
- [ ] OCR 样本集准确率 ≥80%（name+company+title 任一可用）

---

## 2. 測試案例 — P0

### 2.1 連拍收錄（US-2.1）

#### TC-M2-001 | 連拍 5 張成功上傳
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | E2E |
| **Preconditions** | 已登入；有 active capture session |
| **Steps** | 1. 進入 /capture/burst<br>2. 連續拍照 5 次<br>3. 觀察 thumbnail strip |
| **Expected** | 5 張皆出现缩略图；状态 uploading→queued→ocr_processing→ocr_done；用户无需填任何栏位 |

#### TC-M2-002 | 單張 upload 時間 <3s
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | POST /cards with 2MB JPEG + Idempotency-Key |
| **Expected** | 202 回應 <3s；raw_card.status=uploading 或 queued |

#### TC-M2-003 | 部分 upload 失敗不影響其他
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | 5 張 upload；mock 第 3 張 S3 失敗 |
| **Expected** | 1,2,4,5 成功；第 3 張 ❌ 可 retry；session card_count=4 |

#### TC-M2-004 | Idempotency-Key 防重复
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | 同 Idempotency-Key POST 2 次 |
| **Expected** | 仅 1 张 raw_card；第二次回传相同 raw_card_id |

#### TC-M2-005 | 收錄當下零必填
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | E2E |
| **Steps** | 连拍 3 张后直接离开 burst 页面 |
| **Expected** | 无 modal 要求填 source_label/备注；3 张皆 background OCR |

---

### 2.2 OCR 背景處理

#### TC-M2-006 | OCR 成功 → auto_accepted
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | Mock Claude 回传 name/company/title confidence 皆 ≥0.8 |
| **Expected** | review_status=auto_accepted；status=ocr_done |

#### TC-M2-007 | OCR 低信心 → pending_review
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | Unit + Integration |
| **Preconditions** | title confidence=0.6 |
| **Expected** | review_status=pending_review；UI 显示 🟠 dot |

#### TC-M2-008 | OCR 失敗保留原圖
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | Mock Claude 3 次 timeout |
| **Expected** | status=ocr_failed→pending_review；image_url 仍可访问；待确认可手动填 3 栏 |

#### TC-M2-009 | OCR 完成觸發 M3 handoff event
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | Integration |
| **Expected** | handoff queue 收到 ContactUpsertRequested；payload 含 name/company/title |

#### TC-M2-010 | 多語名片 OCR（中/英/日）
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | Manual + Integration |
| **Steps** | 各语言样本 3 张 |
| **Expected** | name 或 company 至少一项 confidence ≥0.5 |

---

### 2.3 延後確認（US-2.2 / DDR-18）

#### TC-M2-011 | 待確認僅 3 欄可編輯
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | Component + E2E |
| **Steps** | 打开 /review/[cardId] |
| **Expected** | 姓名/公司/抬頭 editable；电话/Email readonly grey |

#### TC-M2-012 | 確認 3 欄 → CONFIRMED
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | PATCH /cards/:id/review { name, company, title, version } |
| **Expected** | review_status=confirmed；re-emit handoff |

#### TC-M2-013 | 跳過確認仍可搜尋（R-3）
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | Integration |
| **Preconditions** | pending_review 卡片 |
| **Expected** | handoff 已 emit；M5 可索引（stub 断言 event 存在） |

#### TC-M2-014 | 右滑確認 / 左滑跳過
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | E2E (mobile viewport) |
| **Expected** | 右滑→confirmed toast；左滑→仍 pending |

#### TC-M2-015 | Optimistic lock 409
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | 两个 PATCH 同 card 不同 version |
| **Expected** | 后者 409 VERSION_CONFLICT；UI toast 刷新 |

#### TC-M2-016 | 修改 company 觸發 re-enrich 標記
| 欄位 | 內容 |
|------|------|
| **Priority** | P1 |
| **Type** | Integration |
| **Steps** | review 修改 company 名 |
| **Expected** | handoff payload company 更新；M6 re-enrich event（stub） |

---

### 2.4 Session 與 Aha Moment

#### TC-M2-017 | Session 自動建立與關閉
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | 连拍→点「结束」 |
| **Expected** | session.status=closed；摘要页显示成功/处理中/失败计数 |

#### TC-M2-018 | 30 分鐘 idle 自動關閉 session
| 欄位 | 內容 |
|------|------|
| **Priority** | P1 |
| **Type** | Integration |
| **Steps** | 创建 session；mock 31min；trigger idle job |
| **Expected** | session.status=closed |

#### TC-M2-019 | ≥3 張 OCR 完成 → Aha Modal
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | E2E |
| **Steps** | 首次 onboarding 连拍 3 张等 OCR |
| **Expected** | Modal「现在试试搜索」；Primary→/search |

#### TC-M2-020 | Session 0 成功空狀態
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | E2E |
| **Steps** | 5 张全部 upload 失败→结束 session |
| **Expected** | 摘要「本次 0 张成功」+ CTA 重新收录 |

---

### 2.5 錯誤與恢復

#### TC-M2-021 | Upload retry 3 次
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | Mock 网络 fail 2 次后成功 |
| **Expected** | Banner「重试中 (2/3)」；最终成功 |

#### TC-M2-022 | 不支援圖片格式拒收
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | Upload .pdf |
| **Expected** | 400 VALIDATION_ERROR；Toast 支援格式说明 |

#### TC-M2-023 | 圖片 >10MB 自動壓縮
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | Upload 15MB JPEG |
| **Expected** | 存储 ≤2048px 长边；upload 成功 |

#### TC-M2-024 | Duplicate hash 非阻擋
| 欄位 | 內容 |
|------|------|
| **Priority** | P1 |
| **Type** | E2E |
| **Steps** | 同用户 30 天内扫相同图片 |
| **Expected** | Toast「3 天前可能扫过」+「仍要收录」→ force 新 card |

---

### 2.6 授權與安全

#### TC-M2-025 | 未登入 API 401
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | 无 JWT POST /cards |
| **Expected** | 401 UNAUTHORIZED |

#### TC-M2-026 | 跨用戶存取 403/404
| 欄位 | 內容 |
|------|------|
| **Priority** | P0 |
| **Type** | Integration |
| **Steps** | User A 尝试 GET/PATCH User B 的 card |
| **Expected** | 404（不泄露存在性） |

#### TC-M2-027 | Rate limit 超限 429
| 欄位 | 內容 |
|------|------|
| **Priority** | P1 |
| **Type** | Integration |
| **Steps** | 61 POST /cards in 1 min |
| **Expected** | 429 + Retry-After |

#### TC-M2-028 | URL import SSRF block
| 欄位 | 內容 |
|------|------|
| **Priority** | P1 |
| **Type** | Integration |
| **Steps** | POST import-url `http://169.254.169.254/` |
| **Expected** | 400 UNSUPPORTED_URL |

---

## 3. 測試案例 — P1（電子名片匯入）

#### TC-M2-029 | 貼 vCard URL 成功
| **Priority** | P1 |
| **Steps** | POST /import-url 有效 .vcf 链接 |
| **Expected** | <10s；raw_card 建立；Toast「已收进名片库」 |

#### TC-M2-030 | QR vCard 文字成功
| **Priority** | P1 |
| **Steps** | POST /import-qr BEGIN:VCARD... |
| **Expected** | fields 正确映射；跳过 OCR 或低优先 |

#### TC-M2-031 | 不支援 URL 格式
| **Priority** | P1 |
| **Steps** | POST import-url 无效链接 |
| **Expected** | IMPORT_FAILED；Modal 引导手动新增 |

#### TC-M2-032 | 剪贴板粘贴按钮
| **Priority** | P1 |
| **Type** | E2E |
| **Expected** | 点粘贴→输入框填入剪贴板 URL |

#### TC-M2-033 | OCR daily quota 超出
| **Priority** | P1 |
| **Steps** | 用户当日 OCR >50 |
| **Expected** | OCR_QUEUED_DELAYED；UI「预计 X 分钟」 |

#### TC-M2-034 | 手动新增无图
| **Priority** | P1 |
| **Steps** | POST /cards/manual { name, company, title } |
| **Expected** | 跳过 OCR；直接 pending_review 或 auto_accepted |

---

## 4. 空狀態測試

| ID | 位置 | 条件 | Expected |
|----|------|------|----------|
| TC-M2-E01 | 收錄 Tab | 0 cards | 空状态 +「開始連拍」CTA |
| TC-M2-E02 | 待確認 Tab | 0 pending | 「全部已确认 ✓」 |
| TC-M2-E03 | 待確認 Tab | 全部 auto_accepted | 可选「2 张可核对」 |
| TC-M2-E04 | Session 摘要 | 0 success | 「本次没有成功收录」 |
| TC-M2-E05 | 收錄 Tab | Privacy Strip 常显 | 🔒 預設私人文案可见 |

---

## 5. 無障礙測試

| ID | 检查项 | Expected |
|----|--------|----------|
| TC-M2-A01 | 快门按钮 aria-label | 「拍照收录名片」 |
| TC-M2-A02 | 信心 dot | 不仅靠颜色；有「待确认」文字 |
| TC-M2-A03 | 触控目标 | 快门 ≥44px；确认按钮 ≥44px |
| TC-M2-A04 | 对比度 | Primary text ≥4.5:1 |
| TC-M2-A05 | 键盘 | 待确认表单 Tab 顺序正确 |

---

## 6. 效能基準

| 指標 | 目標 | 測試方法 |
|------|------|---------|
| 单张 upload API | P95 <3s | k6 / Playwright timing |
| OCR 背景完成 | P95 <15s | Worker metric |
| 连拍 10 张 session | 无 UI freeze | Playwright performance |
| 待确认列表 100 张 | 滚动 FPS >30 | Manual profiling |

---

## 7. 自動化對照表

| 测试 ID | 自動化 | CI |
|---------|--------|-----|
| TC-M2-001~005 | Playwright | ✅ nightly |
| TC-M2-006~009 | Vitest integration | ✅ every PR |
| TC-M2-011~015 | Playwright + Vitest | ✅ every PR |
| TC-M2-019 | Playwright | ✅ every PR |
| TC-M2-025~026 | Vitest | ✅ every PR |
| TC-M2-010 | Manual 样本集 | 每 sprint |
| TC-M2-A01~05 | axe-core | ✅ every PR |

---

## 8. Bug Report 模板

```markdown
## [M2-{序号}] {简短标题}

**Severity**: P0-Blocker / P1-Major / P2-Minor / P3-Trivial
**Priority**: 修复优先级（可与 Severity 不同）
**Module**: M2 名片收錄
**Environment**: staging / prod · iOS Safari 17 / Chrome 124 · user_id

### 复现步骤
1.
2.
3.

### 预期结果


### 实际结果


### 证据
- 截图/录屏：
- 相关 raw_card_id：
- API response / Sentry link：

### 备注

```

**Severity 指南（M2）**：
- **P0**：无法收錄、数据泄露、OCR 全部失败无 fallback
- **P1**：待确认流程 broken、handoff 未 emit、Aha modal 不触发
- **P2**：UI 文案/样式、P1 功能（QR/URL）
- **P3**： cosmetic

---

## 9. 驗收清單（M2 Release Gate）

### 功能
- [ ] TC-M2-001 ~ 028 P0 全 Pass
- [ ] 待确认仅 3 栏（TC-M2-011）
- [ ] Aha modal（TC-M2-019）
- [ ] Handoff event（TC-M2-009）

### 安全
- [ ] TC-M2-025 ~ 026 Pass
- [ ] SSRF（TC-M2-028）

### 设备
- [ ] iOS Safari 连拍 smoke
- [ ] Android Chrome 连拍 smoke
- [ ] Desktop Chrome 待确认

### 效能
- [ ] Upload P95 <3s
- [ ] OCR P95 <15s

### 无障碍
- [ ] axe-core 0 critical violations on /capture, /review

---

## 10. Coupling 回歸（M2 鎖定後需其他模組配合驗證）

| 搭配模組 | 回归场景 | 时机 |
|---------|---------|------|
| M3 | handoff → Contact 建立 | M3 QA |
| M5 | auto_accepted 可搜索 | M5 QA |
| M6 | company 变更 re-enrich | M6 QA |
| M1 | JWT workspace_id | M1 QA |

---

*QA M2 v1.0 — SDLC Phase 1*
