# AGENTS.md — SDLC 協作協議

本 repo 使用 `spec/` 作為專案狀態的單一真相來源（由 sdlc-workflow 流程維護）。
任何 AI agent（Claude Code / Cursor / 其他）在本 repo 工作時，遵守以下協議。

> 註：`frontend/AGENTS.md` 是 Next.js 15 的框架規則，與本檔（SDLC 協議）不同，兩者並存。

## 路徑表（找東西先看這裡）

| 內容 | 路徑 |
|------|------|
| 專案事實與已確認決策 | `spec/project-context.md` |
| 模組狀態（誰做到哪、誰阻塞） | `spec/module-register.md` |
| PRD（需求真相來源） | `spec/BSChat_PRD_v2.md`（現行）+ `spec/BSChat_PRD.md`（原版 L1/L2） |
| 技術棧（實作權威 · LOCKED） | `spec/engineering/BSChat_TECH_STACK.md` |
| 系統架構（per-module SA/SD） | `spec/architecture/BSChat_SA-SD_M<n>.md` |
| 模組 PM L3 | `spec/modules/BSChat_PM_M<n>.md` |
| 模組 UI/UX | `spec/design/BSChat_UIUX_M<n>.md`（基礎：`BSChat_Design_Foundation.md`） |
| 模組 ENG | `spec/engineering/BSChat_ENG_M<n>.md` |
| 模組 QA | `spec/qa/BSChat_QA_M<n>.md` |
| 產品討論草案 | `spec/product/`（例 `BSChat_M35_data_source.md`） |
| 後端程式碼 | `backend/app/modules/m<n>_*`、`backend/app/api/v1/`、`backend/app/ai/`、`backend/app/workers/` |
| 前端程式碼 | `frontend/features/<module>/`、`frontend/shared/` |

## 觸發表（什麼時候讀哪個 skill）

| 時機 | 動作 |
|------|------|
| 要開始任何模組的細節工作（設計 / 寫 code / 測試）前 | 跑 module-kickoff（首次完整 kickoff / 後續 delta check）；本 repo 未 vendor skill，請依 `spec/module-register.md` 與對應模組 spec 比對上游是否變動 |
| 完成實作、merge 前 | 做 code review：security（injection / auth / secrets）、正確性（edge cases / error handling）、效能（N+1）、**是否符合該模組 spec 與 PRD** |

## 五條通則

### 1. 動工前先讀狀態
讀 `spec/project-context.md`（不重問已記錄的事）和 `spec/module-register.md`（不做與模組狀態矛盾的工作，例如對「阻塞」模組寫細節 code）。

### 2. 產出可追溯（防歪樓・正向）
任何新功能或重大改動，必須能對應到 PRD 的具體條目。
對應不到 → 停下來問用戶：「這個不在 PRD 裡，是要先補需求，還是我理解歪了？」
不要因為「做得出來」就做。

### 3. 改動要回寫（防歪樓・反向）
完成有意義的改動後，更新 `spec/module-register.md` 對應模組的狀態。
改了需求 → 更新 PRD；改了架構 → 更新架構文件；
任何穩定事實變了 → 在 `spec/project-context.md` 的變更紀錄加一行。

### 4. 模組細節動工前檢查上游
跑 module-kickoff。delta check 必須列出檢查了什麼，不准只寫結論。

### 5. 策略性選擇不沉默決定
架構 pattern、付費服務、對外介面、資料模型大改——先提案（含 1–2 個替代方案與權衡）再動手。
小事（命名、folder 結構、慣例內的工具選擇）自己決定，但在產出中標明。

## 當前焦點（2026-06-11）

M3.5 個人 LinkedIn 補充（Pro）為唯一活躍前線，狀態「實作進行中（未提交）」，有紅旗：
`person_search_provider=mock` 仍輸出假資料、data_source 標籤未動態化、缺 ENG spec、4 項產品決策待定。
詳見 `spec/module-register.md` 與 `spec/product/BSChat_M35_data_source.md`。
