# Project Onboarding Report — BSChat — 2026-06-11

## 為什麼接手

延續既有專案（continuation）。Repo 已有完整 `spec/`（role-based）與 M1–M6 大量實作，但缺 SDLC 常駐狀態檔（`project-context.md`、`module-register.md`、根 `AGENTS.md`）。使用者希望「接續做並補上 onboarding」。

## 手上資產清單

- **PRD**：`spec/BSChat_PRD_v2.md`（v2.3, 2026-05-20，現行）+ `spec/BSChat_PRD.md`（原版，L1/L2 有效）— 雙版本並存，待合併
- **技術棧**：`spec/engineering/BSChat_TECH_STACK.md`（✅ LOCKED v1.1）
- **系統架構 / 模組 spec**：M2/M3/M3.5/M5/M6 皆有 SA-SD + UIUX + QA；M2/M3/M5/M6 有 ENG（**M3.5 缺 ENG**）
- **程式碼**：
  - backend：`app/modules/{m2_capture, m3_contacts, m3_5_person, m5_search, m6_enrichment}`、`app/api/v1/*`、Celery tasks、`app/ai/pipelines`、Alembic migrations（含 008 pro entitlements、009 m35）
  - frontend：`features/{auth, capture, contacts, search, enrichment, actions, person-enrich}`
- **git 歷史**：2 個 commit（初始 M1–M6 foundation；Complete Free plan）。M3.5 與 Pro 相關改動全部**未提交**

## Gap Analysis

| Deliverable | 狀態 |
|-------------|------|
| PRD | complete（v2 現行；🟡 雙版本待合併） |
| 系統架構（技術棧 + per-module SA/SD） | complete |
| Module register | **missing → 本次補建** |
| project-context | **missing → 本次補建** |
| 根 AGENTS.md | **missing → 本次補建**（原僅 frontend/AGENTS.md，為 Next.js 規則非 SDLC） |
| Per-module SA/SD | M2/M3/M3.5/M5/M6 complete；M1/M8 無獨立 spec（設計即如此） |
| Per-module UI/UX | M2/M3/M3.5/M5/M6 complete |
| Per-module 實作 | M1/M2/M3/M5/M6 已實作；**M3.5 進行中（未提交）**；M4 未實作 |
| Per-module QA | M2/M3/M3.5/M5/M6 complete；M1/M8 無 |

**總結**：文件與實作整體一致、成熟度高。唯一活躍前線是 **M3.5（個人 LinkedIn 補充，Pro）**，且有明確未決問題：
1. `person_search_provider = "mock"` — 仍輸出假候選；但 Pro 付費差異化**不得把 mock 標成「LinkedIn 公開資料」**（`spec/product/BSChat_M35_data_source.md` P3、實例 `0c1e6480-…`）。
2. data_source 標籤未動態化（一律標「LinkedIn 公開資料」）→ 需依 `linkedin_profile` / `linkedin_search` / `card_inference` / `unavailable` 動態呈現。
3. M3.5 缺 ENG spec。
4. data_source 草案尚有 4 項待討論的產品決策（同區/分區顯示、失敗 fallback、URL 讀不到處理、額度文案）。

## 用戶目標

接續做下一個功能（continuation）+ 補齊 SDLC 狀態檔。

## 建議切入點

對 **M3.5** 跑完整 `module-kickoff`：它有架構文件但程式碼存在產品層未決問題，kickoff 會在繼續實作前先鎖定上述 data_source 待決問題與「mock 不可冒充 LinkedIn」紅線，並補上缺少的 ENG spec 視角。

其他可選：
- 先用 `pm-role` 把 data_source 4 項待討論決策拍板，再 kickoff。
- 先處理 PRD 雙版本合併。

## 下一個 skill

`module-kickoff`（目標模組：M3.5）。理由：架構已存在、正在寫 code、但有上游（產品決策）未決，符合「模組首次進入後續細節工作前跑完整 kickoff」。
