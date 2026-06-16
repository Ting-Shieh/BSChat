# Project Context — BSChat

最後更新：2026-06-16
PRD 確認日期：2026-05-20（v2.3，現行真相來源；原 PRD L1/L2 仍有效）→ 執行模式

> 本檔由 `project-onboard` 於 2026-06-11 接手既有專案時重建。
> 唯一目的：已經答過的問題不再問第二次（Read-Before-Ask）。

## 一句話定位

為 B2B 業務代表解決「名片交換後價值流失」的問題 — 批次收錄名片後，AI 看懂公司在做什麼、推估個人負責業務，讓使用者用對話式自然語言「反向找出跟當下業務需求有關的潛在商機」。

## 穩定事實（答過就不重問）

- **團隊**：2 人 MVP（1 位 full-stack / AI engineer，1 位 product / design owner）
- **主力技術棧**（`spec/engineering/BSChat_TECH_STACK.md` ✅ LOCKED v1.1）：
  - 前端：Next.js 15 **PWA**（@serwist/next）· TypeScript · Tailwind 4 · shadcn/ui · TanStack Query v5 · Zustand
  - 後端：FastAPI · uv · Python 3.12+ · Pydantic v2
  - 資料：PostgreSQL · SQLAlchemy 2 async · Alembic · asyncpg
  - 佇列：Redis · Celery（worker 獨立進程）
  - AI：Anthropic Claude（`backend/app/ai/`，預留多 provider）
  - 儲存：Cloudflare R2（boto3）
- **預算**：接受付費 SaaS / API；持續 API 成本功能（auto refresh、live 查、LinkedIn 補充）歸 Pro 付費層
- **不能動的部分**：技術棧已 LOCKED；前後端分離（非 Monorepo）；`spec/` 不參與 build、不被 import；REST `/api/v1/*` + OpenAPI 為前後端唯一契約
- **部署 / 運維能力**：frontend → Vercel；backend API + Celery worker → Railway / Fly.io / Render；Postgres → Neon；Redis → Upstash；R2 → Cloudflare。⚠️ 勿在 Vercel Serverless 跑 OCR/enrich worker
- **設計參考與品牌**：`spec/design/BSChat_Design_Foundation.md`（design tokens）；品牌獨特性需求中；搜尋介面以清楚可解釋優先於炫技

## 已確認決策（標日期，rolling adjustment 可改）

- 2026-05-20：技術棧 LOCKED（Next 15 PWA · FastAPI+uv · Swagger · features/shared · 前後端分離）
- 2026-05-20：垂直切片實施順序 = M1-minimal → M2 → M3 → M6 → M5
- 2026-05-20：MVP 核心價值修正（PRD v2）=「看懂公司」+「反向找商機」；公司產品補全 P1 → **P0**
- 2026-05-20：業務方向採對話式即時意圖，不固定儲存 profile（DDR-5）
- 2026-05-20：資料新鮮度三層 = Layer1 cache-at-ingest（Free+Pro）/ Layer2 stale auto-refresh（Pro）/ Layer3 query-time live（Free 試用 / Pro 放寬）
- 2026-05-20：個人職責理解分層 = Free 僅 M3 LLM 推估；Pro/Enterprise 才有 M3.5 LinkedIn+LLM（DDR-74）
- 2026-06-03：M3.5 紅線 — **Pro 不得把 mock / 推論假資料標示為「LinkedIn 公開資料」**；來源以 `data_source` 動態標籤呈現
- 2026-06-11：M3.5 資料來源與呈現 4+1 項拍板（pm-role · DDR-81~85）= 分區呈現 / 混合 fallback / 有 URL 讀不到不扣額度 / card_inference 免費 / data_source 採 6 類。皆對齊既有實作，紅旗 3 解除
- 2026-06-15：Pro 定位 = Free（讓交換名片變有價值）＋「推薦合作的名片」（平台公開商務身份）。後者依賴企業帳號先發布 Pool B（DDR-76/77）→ 列 Stage 2、blocked-by 企業帳號。近期 Pro 可交付＝Stage 1（Layer3 live 查 + Pro 設定 UI）

## Spec 佈局表（AGENTS.md 路徑表的來源）

- spec-root：`spec/`（可見式 · 佈局風格：**role-based**）
- PRD：`spec/BSChat_PRD_v2.md`（現行）+ `spec/BSChat_PRD.md`（原版，L1/L2）— 🟡 待合併為單一 `prd.md`（見變更紀錄）
- 系統架構：`spec/architecture/BSChat_SA-SD_M*.md`（per-module）；技術權威 `spec/engineering/BSChat_TECH_STACK.md`
- 模組 spec：
  - PM L3：`spec/modules/BSChat_PM_M<n>.md`
  - SA/SD：`spec/architecture/BSChat_SA-SD_M<n>.md`
  - UI/UX：`spec/design/BSChat_UIUX_M<n>.md`
  - ENG：`spec/engineering/BSChat_ENG_M<n>.md`
  - QA：`spec/qa/BSChat_QA_M<n>.md`
  - 產品討論草案：`spec/product/`（例 `BSChat_M35_data_source.md`）
- Vendored skills：未 vendor（如需跨工具紀律可後續補 `spec/skills/`）

## 變更紀錄

- 2026-06-16：Stage 1 開工 — **Pro 設定 UI**（`/settings`：方案、用量、auto-refresh、LinkedIn 自動補充）+ **M5 Layer3 live 查**（`POST /search/queries/:id/live-augment`、`query_augmentations` 表、`suggest_live` 觸發、扣 `live_augment` 額度、match_reason「即時查詢」標注；DDR-36 不寫 M6 cache）
- 2026-06-15：Pro 產品定位收斂 + 分階段（PRD §11.5 細化）。Free＝「讓交換名片變有價值」；Pro＝＋「推薦可合作的名片（平台公開商務身份）」。**Pro 靈魂「推薦合作」依賴 Pool B，而 Pool B 只能由企業 Admin 發布（DDR-76/77）→ 必須等企業帳號**。階段：Stage 0（已完成 Pro 自己庫價值）/ Stage 1（可獨立做：Layer3 live 查 + Pro 設定 UI + E2E）/ Stage 2（⏳ 等企業帳號：M11 Pool B → M5b 跨池推薦）。M11/M5b 於 register 標 blocked-by 企業帳號。
- 2026-06-11：M35-009 決策 — 官方 LinkedIn API **待審核未過，擱置**。Pro 上線資料來源僅靠：①有 URL → Gemini 公開搜尋（`linkedin_url_public`「○ 依連結公開摘要」）②無 URL → `card_inference`「○ 名片推估」。**mock/無官方 API 時永不輸出 ✦ LinkedIn**（紅旗 2 收斂為硬化 + 測試，非接 provider）。
- 2026-06-11：`sa-sd-role`（模組模式）更新 `SA-SD_M35` v1.1 對齊 data_source 6 類動態標籤（紅旗 1 解除，R-35.7 作廢），並補 `ENG_M35` v1.0（Python，對齊實際 code；DDR-86~88）。M3.5 剩紅旗 2（mock 防冒充＋接真 provider）為純實作工作。
- 2026-06-11：`pm-role` 拍板 M3.5 data_source 4+1 項決策（DDR-81~85），寫回 PRD §12.5.4、`BSChat_M35_data_source.md` §2/§3、module-register。M3.5 紅旗 3 解除；剩餘紅旗 1（SA-SD 對齊）轉 `sa-sd-role`、紅旗 2（mock 防冒充）為實作。
- 2026-06-11：`project-onboard` 重建狀態檔（project-context、module-register、onboarding report、根 AGENTS.md）。盤點發現 M3.5 為進行中模組（全部未提交），核心缺口 = `person_search_provider=mock` 仍輸出假資料、data_source 標籤未動態化、缺 M3.5 ENG spec。
- 🟡 待辦：PRD 雙版本並存（`BSChat_PRD.md` + `BSChat_PRD_v2.md`），建議合併為單一 `prd.md`（頂端標確認日期），舊版靠 git 歷史。尚未執行。
