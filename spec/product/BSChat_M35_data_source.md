# M3.5 職責補充 — 資料來源與呈現（產品共識草案）

> 狀態：**討論中** · 2026-06-03  
> 背景：Pro 為付費差異化，**不得以 mock 假資料標示為 LinkedIn**（見聯絡人 `0c1e6480-…` 實例）。

---

## 1. 產品原則

| # | 原則 |
|---|------|
| P1 | Pro 付費價值 = **真實 LinkedIn 公開資料** 經 LLM 整理之職責範圍（DDR-74） |
| P2 | 找不到 LinkedIn 時，可顯示 **AI 推論**，但 UI/API **必須標示來源**，不得寫「LinkedIn 公開資料」 |
| P3 | 開發環境 mock 僅供工程測流程，**Pro 帳號不得將 mock 當成交付結果** |
| P4 | 與 Free 的 M3 `responsibility_scope`（名片推估）區隔：Pro 區塊優先顯示 `person_scope`，來源標籤決定信任度 |

---

## 2. 資料來源分類（`data_source`）

> **2026-06-11 定案（DDR-85）**：正式採 **6 類**（修正 6/3 草案僅 4 類、與 code 漂移的問題）。

| `data_source` | 意義 | UI 建議標籤（繁中） | 是否消耗 LinkedIn 月額度 |
|---------------|------|---------------------|---------------------------|
| `linkedin_profile` | 有 URL，且成功讀取真實個人頁片段 | ✦ LinkedIn 個人頁 · AI 整理 · {n}% | 是 |
| `linkedin_search` | 無 URL，搜尋 API 找到候選且 match ≥ 門檻 | ✦ LinkedIn 搜尋 · AI 整理 · {n}% | 是 |
| `linkedin_url_public` | 有 URL 但僅抓到公開網路摘要（非真個人頁片段） | ○ 依連結公開摘要 · AI 整理 · {n}% | 是（手動觸發時） |
| `card_inference` | 未找到 / 無法讀取 LinkedIn，改依名片欄位推論 | ○ 名片推估（未找到 LinkedIn）· AI 整理 · {n}% | **否** |
| `user_manual` | 使用者自行輸入職責 | ✎ 使用者筆記 | 否 |
| `unavailable` | 有 URL 但讀取失敗，且未 fallback | — 顯示空狀態 + 說明 | 否 |

`source_type`（DB 技術欄）對照：`linkedin_url` → `linkedin_profile`；`people_api`（有 URL）→ `linkedin_search`、`people_api`（無 URL，legacy mock）→ `card_inference`；`web_search` → `linkedin_url_public`；`card_inference` → `card_inference`；`user_manual` → `user_manual`。

---

## 3. 使用者流程（建議）

```
[Pro 使用者按「職責補充」]
        │
        ▼
  有 linkedin_url? ──是──► 嘗試讀取真實 LinkedIn
        │                      │
        否                     ├─成功──► linkedin_profile + LLM
        │                      └─失敗──► 搜尋或 fallback
        ▼
  姓名+公司搜尋（真實 API）
        │
        ├─0 筆 / 低 match ──► card_inference（標 ○ 名片推估）
        ├─多筆 ──► 請使用者確認候選
        └─1 筆高 match ──► linkedin_search + LLM
```

**呈現決策（2026-06-11 定案 · pm-role）**

| # | 議題 | 定案 | DDR |
|---|------|------|-----|
| 1 | `person_scope` 與 M3 `responsibility_scope` | **分區**：M3.5 獨立區塊；M3 推估降為「系統參考（名片推估）」置上方（`has_m3_fallback` 旗標） | DDR-81 |
| 2 | LinkedIn 路徑失敗的 fallback | **混合**：有 URL 讀不到 → 停下來問（不自動 fallback）；無 URL 搜尋 0 筆 → 自動 `card_inference` | DDR-82 |
| 3 | 有 URL 但讀不到 | **`unavailable` + `insufficient`**，提示「請確認連結或自行輸入」，**不扣額度** | DDR-83 |
| 4 | `card_inference` 額度 | **免費**：不扣 LinkedIn 月額度、也不扣 M3 額度 | DDR-84 |

> 以上四項皆 = 既有實作行為，本次為產品正式拍板使文件與 code 對齊（紅旗 3 解除）。

---

## 4. 工程現況與缺口

| 項目 | 現況 | 目標 |
|------|------|------|
| Profile 搜尋 | `person_search_provider=mock`，假候選 | Tavily / People API |
| UI 標籤 | 一律「LinkedIn 公開資料」 | 依 `data_source` 動態 |
| Pro + mock | 會寫入假 enrichment | mock 不冒充 LinkedIn；改 `card_inference` 或拒絕 |

---

## 6. 信心門檻與 UI 狀態（2026-06-03 定案）

| 路徑 | 寫入門檻 | 未達門檻 |
|------|----------|----------|
| `linkedin_profile` / `linkedin_search` | confidence ≥ **0.75** | `status=insufficient`，不扣 LinkedIn 月額度 |
| `card_inference` | confidence ≥ **0.65** | 同上 |
| 有交付 | `status=completed` + `person_scope` | — |

- **禁止**：`completed` 但 `person_scope` 為空（舊資料以 `insufficient` 顯示）。
- **UI**：`insufficient` 區塊說明原因 + 導向 M3 + 提示補 LinkedIn。
- **額度**：僅成功寫入且為 LinkedIn 路徑時扣 `person_linkedin` 月額度。

---

## 5. 驗收（Pro 上線前）

- [ ] `person_search_provider != mock` 時，有真實 snippet 才標 `linkedin_*`
- [ ] mock / 無 API 時，Pro 結果僅能為 `card_inference` 或 `unavailable`，UI 不得出現 ✦ LinkedIn
- [ ] 詳情 API 回傳 `data_source` + `provenance_label` 一致
- [ ] 回歸：賴昀君（無 linkedin_url）重新補充 → 標「名片推估」
