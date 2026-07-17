# BSChat SA/SD — M11 v1.1（電子名片 opt-in · PRD v4 delta）

> **版本**：v1.1  
> **日期**：2026-07-14  
> **依據**：kickoff `m11-ecard-optin-20260714.md`、PRD v4 §2.2～2.3／§4、US-v4-4  
> **基底**：`BSChat_SA-SD_M11.md` v1.0（stub CRUD／索引仍有效）；本文只寫 **增量與語意覆寫**

---

## Delta check（M11 · SA/SD）

已檢查 PRD v4（電子名片＋僅企業曝光）、kickoff 2026-07-14 ✅、M1 試用閘已落地、既有 stub API  
→ ✅ 開工 v1.1

---

## 1. 語意覆寫

| v1.0 用語 | v4 用語 |
|-----------|---------|
| public business stub | **電子名片** |
| publish | **允許 AI 推薦**（opt-in 進公開池） |
| unpublish | **關閉 AI 推薦**（離池） |
| Pool B | 公開推薦池 |

**DDR-M11-v4-1**：`status=published` **等同** `allow_ai_recommend=true`；不另加布林欄（避免雙重真相）。Admin UI 文案用「允許 AI 推薦」。

**DDR-M11-v4-2**：僅 `plan_tier=enterprise` + org admin 可 publish（既有閘門不變）。

**DDR-M11-v4-3**：公開展示／分享頁／搜尋結果 **禁止** 電話、Email（既有 stub 無此欄；分享頁亦不得加）。

---

## 2. Schema 增量（`public_business_stubs`）

| Column | Type | 說明 |
|--------|------|------|
| `one_line_blurb` | TEXT NULL | 選填一句話介紹（PRD §2.3） |
| `avatar_url` | TEXT NULL | 選填頭像 URL（外鏈或日後 R2） |

`external_card_url`、姓名／公司／職稱維持必填（title 實務上 Admin 應填；API 維持可 null 但 UI 標必填）。

索引 `search_text` 追加 `one_line_blurb`。

---

## 3. API 增量

### 3.1 Admin stub body 擴充
`StubCreate`／`Update`／`Response` 加 `one_line_blurb`、`avatar_url`（optional）。

### 3.2 公開讀取（無需登入）

| Method | Path | 說明 |
|--------|------|------|
| GET | `/api/v1/public/cards/{stub_id}` | 僅 `status=published`；404 否則 |

**Response**（無電話 Email、無內部 org 敏感）：

```json
{
  "id": "uuid",
  "display_name": "王小明",
  "company_name": "Acme",
  "title": "業務經理",
  "one_line_blurb": "…",
  "avatar_url": null,
  "responsibility_keywords": [],
  "product_keywords": [],
  "external_card_url": "https://…",
  "org_name": "Acme Taiwan"
}
```

**DDR-M11-v4-4**：分享連結 = `{WEB_ORIGIN}/card/{stub_id}`；未 publish 的 id 公開 API 404（防枚舉草稿——可接受 MVP；Later 可改 opaque slug）。

---

## 4. 資料流（opt-in）

```
Admin 編輯電子名片（draft）
  →「允許 AI 推薦」= publish → index Pool B
  → 分享頁／搜尋可見摘要＋外鏈

Admin「關閉 AI 推薦」= unpublish → unindex
  → 分享頁 404；搜尋不可命中
```

⚠️ 不建議 AI 化：opt-in 閘門、索引寫入。

---

## 5. M5b 契約修正（薄）

v1.0 §5.2「free 僅 private」**廢止** → 改遵 `BSChat_SA-SD_M1.md`（Free 終身 2 次）。  
M5b 本輪**不重寫检索**，只確認閘門已接 M1（已做）。

---

## 6. 完成標準

- [x] 語意／欄位／公開 API 寫清  
→ UI/UX → ENG → Code（跳過手動測）  
