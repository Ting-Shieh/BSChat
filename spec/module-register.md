# Module Register / 模組註冊表 — BSChat

最後更新：2026-07-09（產品重審：凍結下游擴張）

> ⚠️ **2026-07-09 產品重審凍結令**：核心價值經真實用戶驗證前，**暫停一切下游擴張投入** — 不再新增 Pool B（M11）、跨池搜尋（M5b）、企業版、額外 embedding 調校等工作。焦點=①殺手時刻畫面（`spec/screens/screen-1-opportunity-briefing.html`）②拿去給真實 B2B 業務測「拉力」。已實作模組維持現狀、不回退；只是**不再往下加碼**。詳見 `project-context.md` 2026-07-09。
>
> 🎯 **產品形狀（2026-07-13 確認 · A+C）= AI 團隊聯絡人情報工具**，**v1 dogfood 自家公司**（業務團隊＋業務助理＋採購共用一池），**願景對外賣給業務團隊/公司**。核心＝把一池名片 AI 自動讀懂（公司產品、個人職責、**特質/經歷/合作可能性**——取代業務助理手工表格），並讓團隊在需求當下反向找對的人/公司。
> - **v1 核心（un-parked）**：團隊共享池 + AI 自動 dossier + 對話式反向搜尋（商機簡報）+ 沉睡喚醒。CRM/dossier **不再是 non-goal**（是業務助理真實工時痛）。
> - **Later / 願景（不進 v1）**：外部供應商發現池（雙邊/Pool B/M11/M5b）、對外消費者版、收款後台、多租戶。
> - **待 v3 處理的反轉**：舊「預設私密·單機」→ **團隊共享池**（衝擊 M7、DDR-59/62）。
> - 先前 7/9「Primary persona＝單一業務個人、park CRM」已由 7/13 覆寫，見 `project-context.md` 2026-07-13。

## 系統一句話定位

AI 驅動的名片管理平台：批次收錄 → AI 看懂公司 → 對話式反向找商機（PRD v2）。

## 模組清單

| # | 模組 | 一句話目的 | 對應 PRD | 當前階段 | 最近 kickoff / delta check | 紅旗 / 阻塞 |
|---|------|----------|---------|--------|--------------------------|------------|
| M1 | 帳號 / 訂閱 | dev login + JWT + plan/entitlement + **Account Hub（§11.8）** | §11.3 G、§11.8~9、DDR-96~98 | **Stage 1b 已實作**（AI 嚴格度 + 設定頁） | PRD v2.5 | – |
| M2 | 名片收錄 | 批次連拍 + 背景 OCR + URL/QR/vCard 匯入 + 延後最低確認 | §5.2 P0、US-2.x | 已完成 - 待驗證（committed；少量 import 編輯未提交） | – | – |
| M3 | 聯絡人 + 職責推估 | 結構化聯絡人 + M3 LLM 個人負責業務推估 | §5.2 P0、US-6.2、DDR-8/9 | 已完成 - 待驗證（committed） | – | – |
| M3.5 | 個人 LinkedIn 補充 | Pro：LinkedIn 公開資料 + LLM → 職責摘要 | §11.2.1 C、§12.5（含 DDR-81~85）、DDR-74/75/76、SA-SD v1.1、ENG v1.0 | **Pro 就緒（committed；code review 過）** | kickoff＋pm＋sa-sd v1.1＋ENG v1.0＋M35-010＋review F1~5 皆 2026-06-11 | ✅ 紅旗 1/2/3 全解除、防冒充有測試、58 passed；⛔ M35-009 接官方 LinkedIn API 擱置（API 待審核，以 Gemini 公開搜尋 + card_inference 過渡） |
| M5 | AI 搜尋（Pool A + **Pro 跨池**） | 对話式反向搜尋 + 精準度分級 + 可信度 UX | §5.2、§11.8~9、US-5.3、DDR-99~101、F-5.22 | **DDR-101 + pgvector + dev debug 面板** 已实作 | migration 014 · PM v1.2 | – |
| M5b | 跨池搜尋（自己庫 + 公開目錄） | Pool A + Pool B → Pro 搜公開商務身份/推薦合作 | §11.5 Stage 2、§13.1、DDR-58/80 | **已實作** | M11 MVP | – |
| M6 | 公司補全 | 收錄時 enrich 主要產品 + provenance + 手動更新 + Pro stale refresh | §12、US-6.x、DDR-34~37 | 已實作（Free + Pro Layer2 + **query_time_extract 供 M5**） | – | – |
| M7 | 隱私 | 預設私密 Pool A + user_id 過濾 + 軟刪除 | §FR 隱私 P0、DDR-59/62 | 已隨各模組實作 - 待驗證 | – | – |
| M8 | 匯出與行動 | 一鍵複製電話 / Email（純前端 MVP） | §5.2 P1、US-8.1、S-04 | 已實作（MVP，無獨立 spec） | – | – |
| M4 | 重複偵測（P1） | Email / 電話比對提示 | §5.2 P1、原 PRD P0 | 未實作 | – | – |

### Phase 2 / 3（schema 預留，MVP 不實作）

| # | 模組 | 目的 | 對應 PRD | 階段 |
|---|------|------|---------|------|
| M11 | 企業公開商務目錄（Publisher） | Admin 發布 stub → **Pool B**（Pro 跨池搜尋資料來源） | §11.3 E、§11.5 Stage 2、§13、DDR-60/76~80 | **M11 MVP 已實作**（含已發布 stub 編輯 UI） | [kickoff 2026-06-16](kickoffs/m11-20260616.md) · migration 011 | – |

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
