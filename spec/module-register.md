# Module Register / 模組註冊表 — BSChat

最後更新：2026-06-16（Stage 1：Pro 設定 UI + M5 Layer3 live 查實作）

## 系統一句話定位

AI 驅動的名片管理平台：批次收錄 → AI 看懂公司 → 對話式反向找商機（PRD v2）。

## 模組清單

| # | 模組 | 一句話目的 | 對應 PRD | 當前階段 | 最近 kickoff / delta check | 紅旗 / 阻塞 |
|---|------|----------|---------|--------|--------------------------|------------|
| M1 | 帳號 / 訂閱 | dev login + JWT + plan/entitlement 開關 | §11.3、TECH_STACK §10 | 已實作（Free + Pro entitlements/plan switch/**設定頁**） | – | – |
| M2 | 名片收錄 | 批次連拍 + 背景 OCR + URL/QR/vCard 匯入 + 延後最低確認 | §5.2 P0、US-2.x | 已完成 - 待驗證（committed；少量 import 編輯未提交） | – | – |
| M3 | 聯絡人 + 職責推估 | 結構化聯絡人 + M3 LLM 個人負責業務推估 | §5.2 P0、US-6.2、DDR-8/9 | 已完成 - 待驗證（committed） | – | – |
| M3.5 | 個人 LinkedIn 補充 | Pro：LinkedIn 公開資料 + LLM → 職責摘要 | §11.2.1 C、§12.5（含 DDR-81~85）、DDR-74/75/76、SA-SD v1.1、ENG v1.0 | **Pro 就緒（committed；code review 過）** | kickoff＋pm＋sa-sd v1.1＋ENG v1.0＋M35-010＋review F1~5 皆 2026-06-11 | ✅ 紅旗 1/2/3 全解除、防冒充有測試、58 passed；⛔ M35-009 接官方 LinkedIn API 擱置（API 待審核，以 Gemini 公開搜尋 + card_inference 過渡） |
| M5 | AI 搜尋（Pool A） | 對話式反向搜尋 + 匹配理由 + 硬條件 NO_MATCH | §5.2 P0、US-5.x、DDR-73 | 已實作 Pool A + **Layer3 live 查（Stage 1）** | – | ⏳ Stage 2 跨池公開搜尋 blocked-by 企業帳號（M5b） |
| M6 | 公司補全 | 收錄時 enrich 主要產品 + provenance + 手動更新 + Pro stale refresh | §12、US-6.x、DDR-34~37 | 已實作（Free + Pro Layer2 + **query_time_extract 供 M5**） | – | – |
| M7 | 隱私 | 預設私密 Pool A + user_id 過濾 + 軟刪除 | §FR 隱私 P0、DDR-59/62 | 已隨各模組實作 - 待驗證 | – | – |
| M8 | 匯出與行動 | 一鍵複製電話 / Email（純前端 MVP） | §5.2 P1、US-8.1、S-04 | 已實作（MVP，無獨立 spec） | – | – |
| M4 | 重複偵測（P1） | Email / 電話比對提示 | §5.2 P1、原 PRD P0 | 未實作 | – | – |

### Phase 2 / 3（schema 預留，MVP 不實作）

| # | 模組 | 目的 | 對應 PRD | 階段 |
|---|------|------|---------|------|
| M11 | 企業電子名片（Publisher） | 建立公開員工電子名片 → **Pool B**（Pro「推薦合作名片」的資料來源） | §13、§11.5 Stage 2、DDR-60/76/77 | 未啟動（Stage 2 · ⏳ blocked-by 企業帳號：Pool B 只能由企業 Admin 發布） |
| M5b | Network 跨池搜尋 | Pool A + Pool B → Pro 搜公開商務身份/推薦合作 | §13.1、§11.5 Stage 2、DDR-58 | 未啟動（Stage 2 · ⏳ blocked-by M11/Pool B） |

## 模組依賴圖

```
[M1 帳號/訂閱] ──(entitlement gate)──► [M3.5]、[M6 Pro refresh]
       │
[M2 收錄] ──► [M3 聯絡人/推估] ──► [M5 搜尋]
       │              │
       └──► [M6 公司補全] ──► (觸發 M3 pass2 + M5 re-index)
                      │
                [M3.5 個人補充]（Pro，gate 自 M1）
       [M7 隱私] 橫切全部 · [M8 行動] 接 M3/M5 結果
```

## 標籤說明（本次 onboarding 使用）

- `已完成 - 待驗證` — code 與文件都有，尚未交叉稽核確認一致
- `已實作（Free）+ <X> 進行中` — Free 範圍 committed，Pro 部分未提交
- `Kickoff 通過 — 實作進行中` — 有 code 但未提交且有未決問題

## 維護原則

- M3.5 首次進入後續細節工作前 → 跑**完整 module-kickoff**（鎖定 data_source 待決問題與 mock 紅線）
- 每階段完成 → 更新「當前階段」（反向追溯）；發現紅旗 → 改「阻塞」並寫清楚原因
- PRD / 系統架構更新 → 頂端標註日期，受影響模組重跑完整 kickoff
