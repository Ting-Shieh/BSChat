# BSChat PM L3 — Module 2：名片收錄（含 OCR）

> **版本**：v1.0（2026-05-20 補寫；含 DDR-18 三欄確認修正）  
> **狀態**：PM L3 ✅ 可鎖定  
> **依據**：`BSChat_PRD_v2.md` §2 S-02/S-03、§5–7、DDR-10~20

---

## 模組定位

> M2 的價值不是「把名片存進資料庫」，而是**用最低摩擦把名片收進系統，讓 M5/M6 有資料可以「看懂公司、找商機」**。  
> 使用者最多只願意花 **10 分鐘**試用 —— **收錄必須快到像拍照，而不是像填表。**

**三軌收錄入口（v2）**：

```
┌─────────────┬───────────┬───────────┐
│ 紙本連拍     │ 貼連結     │ 掃 QR     │
│ （P0 核心）  │ （P1）     │ （P1）    │
└─────────────┴───────────┴───────────┘
              ↓
        同一個名片庫（M3 Contact）
              ↓
     背景 OCR + M6 補全 + M3 推估
              ↓
        M5 對話式搜尋
```

---

## L3.1 — Sub-features

| # | Sub-feature | 優先 | 場景 | 驗收標準 |
|---|-------------|------|------|---------|
| F-2.1 | **批次連拍模式** | **P0** | S-02 展覽 | 連續拍照不需每張確認；單張 upload < 3 秒 |
| F-2.2 | 相簿選圖上傳（單張/多張） | P0 | 展後補掃抽屜 | JPEG/PNG/HEIC；>10MB 自動壓縮 |
| F-2.3 | 背景 OCR + 結構化欄位擷取 | **P0** | 全部紙本 | 姓名/公司/職稱/電話/Email/地址/website；背景不阻塞 |
| F-2.4 | **延後最低確認**（姓名/公司/抬頭） | **P0** | DDR-11/18 | 收錄當下零必填；待確認可稍後處理 |
| F-2.5 | CaptureSession（批次掃描會話） | P0 | S-02 | 同場合連拍歸一 session；可選填 source_label |
| F-2.6 | 獨立卡片狀態機 | P0 | N-06 | 單張 OCR 失敗不影響同批次其他張 |
| F-2.7 | 上傳 retry + 進度顯示 | P0 | 展場弱網 | 網路錯誤自動 retry ≤3 次 |
| F-2.8 | **貼連結匯入**（URL paste） | **P1** | S-03 | LINE/Email 連結 → 貼上 → 自動解析 |
| F-2.9 | **QR code 掃描匯入** | **P1** | S-03 | 展場掃 QR → 直接建立 RawCard |
| F-2.10 | 重複上傳提示（image hash） | P1 | 展覽誤觸 | 30 天內同 hash 提示 + 允許 force |
| F-2.11 | 手動新增（無圖） | P1 | 無名片圖 | 跳過 OCR，直接進待確認 |
| F-2.12 | CSV 匯入 | **P2** | 原 PRD | **DDR-16** 延後：訪談未驗證 |
| F-2.13 | 手機聯絡簿匯入 | P2 | 原 PRD | 同上延後 |
| F-2.14 | 離線拍照暫存 | **不做** | — | **DDR-17**：MVP 不支援離線 |

**明確不做（MVP）**：
- ❌ LINE 原生「分享給 BSChat」（DDR-14；使用者接受貼連結/掃 QR）
- ❌ 收錄當下必填備註/分類（DDR-11）
- ❌ CSV / 聯絡簿大量匯入（DDR-16，P2）

---

## L3.2 — State Machine

### 紙本連拍（主流程）

```
[CAPTURE_INIT]
   │ 連拍 / 選圖
   ▼
[UPLOADING] ──(fail, retry≤3)──► [UPLOAD_FAILED]
   │ success                          ├─ retry → [UPLOADING]
   ▼                                  └─ discard → [DISCARDED]
[QUEUED]
   ▼
[OCR_PROCESSING] ──(error)──► [OCR_FAILED]
   │ success                      └─ fallback → [PENDING_REVIEW]（保留原圖）
   ▼
[OCR_DONE]
   ├─ 姓名+公司+抬頭 confidence 皆 ≥ 0.8 → [AUTO_ACCEPTED]
   └─ 任一 < 0.8 → [PENDING_REVIEW]
   │
   │ 使用者延後確認（只改姓名/公司/抬頭）
   ▼
[CONFIRMED] ──handoff──► M3 Contact upsert
                │
                └─ M3 触发 M6 enrich（若 company 有值）

[DISCARDED] ← 任何階段可丟棄
```

### URL / QR 匯入（P1）

```
[PASTE_URL | SCAN_QR]
   ▼
[RESOLVING] ──(無法解析)──► [IMPORT_FAILED]
   ▼
[EXTRACTED] → RawCard（capture_method = url | qr）
   ▼
[OCR_DONE] 或 [AUTO_ACCEPTED]（欄位已結構化時可跳過 OCR）
```

### CaptureSession

```
[SESSION_ACTIVE] ──(使用者結束 OR 30min idle)──► [SESSION_CLOSED]
```

---

## L3.3 — 與下游模組邊界

```
M2 RawCard + OcrResult
    → ContactUpsertRequested（async）
M3 Upsert Worker
    → Contact + provenance
    → CompanyEnrichRequested（若 company 有值）
    → inference pass 1 + index
M6 enrich → M3 pass 2
M5 搜尋（经 M3 index）
```

**M2 不直接呼叫 M6**；公司补全由 M3 handoff 后触发。

---

## L3.4 — Data Entities

### CaptureSession

```
id, user_id, workspace_id
source_type          ← event|meeting|referral|import|other
source_label         ← 如 "Computex 2026"，可事後批次套用
status               ← active|closed
card_count, confirmed_count, pending_count
started_at, closed_at
```

### RawCard

```
id, capture_session_id?, user_id, workspace_id
capture_method       ← camera_burst|upload|manual|url|qr
image_url, image_hash
source_type, source_label
status, review_status
idempotency_key, version
created_at, updated_at
```

### OcrResult

```
id, raw_card_id（1:1）
engine, engine_version
raw_text
extracted_fields     ← jsonb
field_confidences    ← jsonb
overall_confidence
processed_at, duration_ms
```

### ImportJob（P1）

```
id, raw_card_id, input_url, resolver_type
status, error_code
```

### M2 → M3 Handoff 契約

```json
{
  "eventId": "uuid",
  "userId": "uuid",
  "workspaceId": "uuid",
  "rawCardId": "uuid",
  "captureMethod": "camera_burst",
  "sourceType": "event",
  "sourceLabel": "Computex 2026",
  "fields": {
    "name": "王小明",
    "company": "ABC Tech",
    "title": "OEM 業務經理",
    "phones": ["0912-345-678"],
    "emails": ["wang@abc.com"],
    "address": null,
    "website": "https://abc-tech.com.tw"
  },
  "fieldConfidences": {
    "name": 0.95,
    "company": 0.72,
    "title": 0.68
  },
  "provenance": { "source": "ocr", "sourceRef": "raw_card_id" },
  "imageUrl": "r2://...",
  "reviewStatus": "auto_accepted",
  "occurredAt": "2026-05-19T14:00:00Z"
}
```

完整 TypeScript 定义见 `spec/architecture/BSChat_SA-SD_M2.md` §6.1。

---

## L3.5 — Rules

| ID | 規則 |
|----|------|
| R-1 | 收錄當下**零必填**；source_label 可事後套用整個 CaptureSession |
| R-2 | 延後確認**只允許編輯姓名、公司、抬頭**；電話/Email/地址由 OCR 处理 |
| R-3 | `auto_accepted` / `pending_review` 皆 emit handoff；**可進 M5 搜尋**（DDR-22） |
| R-4 | OCR 失敗保留原圖 → `pending_review`；可手动填三栏 |
| R-5 | 单张 upload P95 < 3s；OCR 背景 P95 < 15s |
| R-6 | 圖片 >10MB 壓縮至長邊 2048px |
| R-7 | OCR 支援中（繁/簡）/ 英 / 日；韓文 P1 |
| R-8 | 重複 hash **非阻擋**；duplicate_warning + force 收录 |
| R-9 | ≥3 張 OCR 完成 → Aha「試試搜尋」引导（DDR-10） |
| R-10 | URL 解析失败 → 明确错误 + 引导手动新增（DDR-13） |
| R-11 | 電子名片成功 → UI「已收進名片庫，之後可搜尋」（DDR-13） |
| R-12 | 跳過待確認不惩罚；卡片保持 pending 仍可搜尋 |

---

## L3.6 — 5 Diagnostic Angles

### Upstream

| 來源 | 契約 |
|------|------|
| 使用者 | 連拍/選圖/貼 URL/掃 QR/手动（P1） |
| M1 | `user_id` + `workspace_id`（MVP personal workspace） |
| Claude Vision | 圖片 → 結構化欄位 + 信心度（DDR-19） |
| R2 | `image_url` |
| URL Resolver（P1） | vCard/HTML（DDR-20） |

### Downstream

| 模組 | 消費 |
|------|------|
| **M3** | ContactUpsertRequested — **極高** 契約穩定 |
| **M6** | 经 M3：`company_name` 触发 enrich |
| **M5** | 经 M3 index；`source_label` 可搜 |
| **M7** | RawCard/image cascade 刪除 |
| **M9** | card_uploaded, ocr_completed, card_reviewed |

### Who-else（並發）

- 展覽 10 張並發 upload/OCR：以 `raw_card_id` 為粒度
- 跨裝置：server-side state 為準
- M3 編輯公司名 → re-handoff → M6 re-enrich
- Session 計數原子更新

### Failure

| 失敗 | 行為 | UX |
|------|------|-----|
| 上傳斷線 | retry ≤3 | UPLOAD_RETRYING |
| OCR 失敗 | pending_review + 原圖 | 手动填三栏 |
| URL 無法解析 | IMPORT_FAILED | 改贴连结/手动新增 |
| Session 0 成功 | 仍可 close | 「本次 0 張成功」 |

### Data-reuse

| 資料 | 使用者 |
|------|--------|
| source_type / source_label | M5 篩選、M9 分析 |
| field_confidences | M3 UI、M5 权重 |
| raw_text | M5 索引召回 |
| capture_method | M9、M5 來源篩選 |
| provenance | M3/M7 審計 |

---

## L3.7 — User Stories

**US-2.1 展覽連拍零摩擦**
> As a B2B 業務代表, I want to 在展覽連續拍照收名片, so that 我可以在 10 分鐘內收錄而不需要當場整理。

Acceptance Criteria:
- Given 連拍模式, When 連拍 5 張, Then 5 張皆 upload + 背景 OCR，我無需填任何欄位
- Given 第 3 張 upload 失敗, When 其他張成功, Then 失敗張可 retry，不影響其他
- Given OCR 完成 ≥3 張, When 首次 onboarding, Then 引導「試試搜尋」Aha moment
- Given 我拍完離開 App, When 背景繼續 OCR, Then 下次打開可見結果

**US-2.2 延後最低確認（三欄）**
> As a B2B 業務代表, I want to 之後只快速確認姓名、公司和抬頭, so that 收名片不會變成整理工作。

Acceptance Criteria:
- Given 待確認列表, When 我確認姓名/公司/抬頭, Then → CONFIRMED，触发 M3 handoff
- Given 信心度低, When 我跳過確認, Then 仍 `pending_review` 但**可搜尋**（R-3/R-12）
- Given 待確認 UI, When 打开单张, Then **仅 3 栏可编辑**；电话/Email readonly

**US-2.3 貼連結收電子名片（P1）**
> As a B2B 業務代表, I want to 複製 LINE 上的電子名片連結貼到 BSChat, so that 電子名片不會再留在聊天記錄裡消失。

Acceptance Criteria:
- Given 有效 URL, When 貼上, Then < 10 秒建立 RawCard + 「已收進名片庫」
- Given 無法解析 URL, When 貼上, Then 明确错误 + 引导手动新增

**US-2.4 展覽 QR 掃描（P1）**
> As a B2B 業務代表, I want to 掃描對方的 QR code 直接收進 BSChat, so that 電子名片跟紙本名片在同一個地方。

Acceptance Criteria:
- Given 有效 vCard QR, When 掃描, Then RawCard 建立 + handoff M3
- Given 无效 QR, When 掃描, Then IMPORT_FAILED + 引导

---

## L3.8 — Coupling Check

| 目標模組 | M2 施加的約束 |
|---------|-------------|
| **M1** | 提供 `user_id` + `workspace_id`（可極簡 stub） |
| **M3** | 接受 handoff JSON；支持 auto_accepted Contact |
| **M6** | 由 M3 监听 company 就绪（M2 不 direct call） |
| **M5** | 可搜 source_label + 未确认卡片 |
| **M7** | RawCard/image cascade 删除策略 |

---

## DDR（M2 模組）

| ID | 決策 |
|----|------|
| DDR-16 | CSV/聯絡簿匯入延後 P2（訪談未驗證） |
| DDR-17 | MVP 不支援離線拍照暫存 |
| DDR-18 | 待確認欄位 = **姓名 + 公司 + 抬頭**（訪談修正） |
| DDR-19 | OCR = Claude Vision LLM-first（SA/SD 锁定） |
| DDR-20 | URL/QR MVP = vCard + HTML fallback |
| DDR-21 | auto_accepted 仍 emit handoff |
| DDR-22 | pending_review 仍可被 M5 索引 |

*DDR-10~15 见 PRD v2 §4（产品层）*

---

## Open Blockers → SA/SD

| 🚧 | 議題 | 狀態 |
|----|------|------|
| B-1 | OCR 引擎選型 | ✅ DDR-19 |
| B-4 | Aha 最低名片数 | ✅ ≥3 张 |
| B-5 | URL/QR 格式 | ✅ DDR-20 |

---

## Success Metrics（M2 相关）

| 指標 | MVP 目標 | 依據 |
|------|---------|------|
| 单张 upload | < 3 秒 | S-02 |
| OCR P95 | < 15 秒 | SA/SD |
| 10 分钟内收录 ≥3 张 | > 70% 用户 | DDR-10 |
| Aha moment rate | > 60% | DDR-10 |

---

## 下游文件对齐

| 文件 | 状态 |
|------|------|
| `spec/architecture/BSChat_SA-SD_M2.md` | ✅ v1.0 |
| `spec/design/BSChat_UIUX_M2.md` | ✅ v1.0 |
| `spec/engineering/BSChat_ENG_M2.md` | ✅ v1.0 |
| `spec/qa/BSChat_QA_M2.md` | ✅ v1.0 |

**M2 PM L3：✅ 可锁定（与六角色规格一致）**

---

*PM M2 L3 v1.0 — SDLC Phase 1（2026-05-20 補寫）*
