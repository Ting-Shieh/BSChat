# Kickoff: M5 多輪搜尋＋對話紀錄 · 2026-07-21

## 1. 模組目的（一句話複習）
找人／商機的 **多輪搜尋**：同一串可追問、可回看歷史；瀏覽公開池類意圖可列池。  
對應 PRD v4 §5.1、DDR-v4-17；原型 `spec/screens/screen-9-multiturn-search.html`（已確認）。

## 2. 在系統架構裡的位置
- 上游：M1 entitlement／公開試用、M3 私庫索引、M11／M5b 公開池、既有 Plan UI
- 下游：商機簡報、結果卡行動
- 介面：`POST /search/queries`（+`session_id`）、`GET /search/sessions`、`GET /search/sessions/{id}`、`SearchPage` 對話串＋紀錄

## 3. 存在性審視（強制三問）
- [x] 還該存在？→ **是**（殺手時刻載體；痛點＝單次覆蓋＋無歷史）
- [x] 範圍？→ **多輪搜尋＋紀錄＋瀏覽公開池**；非 IM／閒聊
- [x] 依賴？→ **是**；沿用 M5 retrieval／rerank；補 `search_sessions`

> 判斷：M5 仍合理；相對 2026-07-14 Plan UI kickoff，上游新增 DDR-v4-17 → **完整 kickoff**（非 delta）。

## 4. 自上次工作以來，上游有變動嗎？
- PRD：§5.1／DDR-v4-17；企業成員旅程／名片連結文案（不直接阻塞搜尋）
- 系統架構：SA-SD_M5 曾預留 `search_sessions`（migration 未建）
- project-context：screen-9 確認
- 鄰近：M11 公開池已有 indexed stubs

## 5. 本次 session 範圍
- 階段：**SA 精簡 + Backend + Frontend**
- 產出：
  1. migration `026_search_sessions`
  2. sessions list／detail API；query 綁 session；瀏覽公開池捷徑
  3. SearchPage：多輪氣泡＋紀錄 sheet＋新對話
- 完成標準：可回看上次問題；「公開商務有誰」能列公開池；追問可延續同一串

## 6. 🚩 紅旗
無阻塞。已知：完整 LLM 對話狀態機／跨串合併＝Later；本次用 session + 追問上下文拼接即可。

## 7. 決議
- [x] 通過，開工（用戶「好」）
