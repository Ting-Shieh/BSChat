# Project Context — BSChat

最後更新：2026-07-13（dogfood 收錄 UX 定案 · 僅保留收錄人）
PRD 現行：**`BSChat_PRD_v3.md`（草案，範圍/persona/可見模型真相來源，待 dogfood 驗證）**；v2 核心價值與負面情境延續；原 PRD L1/L2 仍有效
⚠️ 2026-07-13 重定位：BSChat＝AI 團隊聯絡人情報工具，v1 dogfood 自家公司→願景對外。凍結下游擴張仍有效（外部池/雙邊/收款＝Later）。詳見變更紀錄。

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
- 2026-06-17：M5 检索契约（DDR-101）= 统一漏斗 + 两种分数分工；精準度改 rerank prompt，废止服务端 min_match_score 过滤
- 2026-07-09：**產品重審結論（pm-role 重審模式）= 「先驗證核心，再談擴張」**。
  - 診斷：問題**不在** AI 執行品質（用戶未回報搜錯/補錯），而在 (1) 核心從未經真實用戶驗證（13 個月僅創辦人自測；PRD 本質為一次自我訪談），(2)「反向找商機」被實作成**搜尋框**，差異只活在「概念」層、未落到「使用當下」的體感 → 因此感覺與市面收納 App 無異。
  - 用戶確認：市場確實無「把沉睡名片庫在需求出現當下轉成可行動商機」的成品（真實白地）；且**可取得一位真實 B2B 業務**做驗證。
  - 決策：**凍結一切下游擴張投入**（Pool B / M5b 跨池 / 企業版 / 更多 embedding 調校），焦點轉為 ①把殺手時刻做成有感畫面 ②拿去給真實業務測「拉力」。金礦 vs 墳場以真實用戶反應裁定，不再靠內部辯論。
  - 產出：殺手時刻關鍵畫面原型 `spec/screens/screen-1-opportunity-briefing.html`（商機簡報式回應，非搜尋列表）。
  - 待驗證後再定：是否大改 PRD（現在改只是換一組未驗證假設）。
- 2026-07-13：**dogfood 收錄／團隊池 UI 定案（展場討論後收斂）**。
  - **真實流程**：辦公室一批批掃名片（非展場邊走邊收）；團隊多人各自掃入 → **共享池可搜**仍需要。
  - **列表/metadata 只保留「誰收錄」**（`captured_by_name`／「👤 由 X 收錄」）— 追內部知情者；**不強調場合標籤／分區代號**。
  - **明確不做（v1）**：Google Maps／GPS 自動抓地點、展場分區快選、地圖相關 UI — 與核心（AI 看懂＋反向找商機）無關。
  - **推遲（有痛點再做）**：同一人多人收錄 →「Alice 等 N 人」摺疊＋底部彈層；同一人一筆合併；搜尋層去重。
- 2026-07-09（同日 · persona 岔路收斂）：探討過「總經理秘書/高階特助 = 關係維護型輕量 CRM」是否為更強 wedge，**結論：不採用，劃出範圍外（parked）**。
  - **關係生命週期切分**：陌生 →[陌開]→ 認識 →[熟化]→ 常往來。**BSChat 只做前半段（陌開/把人脈轉商機）**；CRM/關係維護屬「熟化後」，是紅海且引擎相反（人工細養 vs AI 推估），非本產品。
  - **Primary persona 鎖定 = B2B 業務代表**（回歸並確認 PRD DDR-6 核心，但這次帶信念、有收斂）。CRM/備註/喜好維護 = 明確 non-goal（未來若真實訊號強再議，預設不做）。
  - **產品定位（共通 job / 品類語言）**：BSChat = 「商務關係的外接大腦——在需要的那一刻，把對的人與對的脈絡遞到手上」。呼應 Design Foundation §1「商務關係智慧平台 · 非 CRM · 非電子名片產生器」。此為**定位白地**（市場多的是「存名片」與「CRM」，少有人定位在「關鍵時刻的關係記憶/商機」）。

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

- 2026-07-13：**Dogfood 部署路徑（方案 B）** — 同事無法用本機 localhost；採 Vercel 前端 + Railway API + Neon（pgvector）+ Upstash Redis + R2 圖檔。Dev 登入＋公司代號即可，暫不做正式註冊。產物：`backend/Dockerfile`、`.env.dogfood.example`、`frontend/.env.dogfood.example`、清單 `spec/product/BSChat_dogfood_deploy.md`。
- 2026-07-13：**其餘頁面對齊 screen-2／screen-flow** — 待確認改大卡（只確認姓名／公司＋跳過／確認）；設定頁改 Account Hub「我的」（帳號卡／用量條／精準度／團隊隱私／升級 CTA）；收錄首頁連拍 hero；底欄 5 tab（搜尋·名片庫·＋收錄·待確認·我的）。CardListItem 加 `version` 支援一鍵確認。
- 2026-07-13：**UI 對齊原型（驗證後施工）** — 依據 `screen-1`/`screen-2` + PRD v3 + 7/13 定案。P0：PrivacyStrip「僅團隊內可見」、tab「名片庫」。P1：名片庫標題／篩選 chip（全部·沉睡·待確認）／列表 AI 藍條＋沉睡＋收錄人；後端 list 加 `created_at`/`dormant_months`。P2：詳情 header chips＋撥號/Email/複製＋①②③ 三區標籤。P3：登入加「公司代號」任意方案可進同一 org。P4：搜尋結果顯示問句泡泡。不做：地圖／分區／screen-3 dossier 三欄。
- 2026-07-13：**dogfood 收錄 UX 定案** — 用戶確認辦公室批次掃描為主流程；團隊共享池保留；聯絡人列表**僅顯示收錄人**（`由 X 收錄`），場合標籤／分區／Google Maps 自動地點 **v1 不做**；多人收同一人之摺疊 UI／實體合併 **等有重複痛點再議**。見「已確認決策」2026-07-13 條。
- 2026-07-13：**實作 A 團隊共享池（最小，順序 C→B→A 完成）**。用戶確認範圍：只做 L2 內部團隊池、L3 外部付費搜尋(network scope)不動。**零新增欄位**：`contacts.user_id` 本即「收錄人」，把可見性從「== 我」擴成「∈ 同 org 成員(OrgMember)」。新 helper `app/core/team.py::get_team_user_ids`(無 org → 只有自己，向後相容)；`get_contact`/`list_contacts`(upsert.py)、`retrieve_candidates`＋`_private_*` 私有池 SQL 改 `= ANY(:user_ids)`、`count_indexed`、`should_suggest_live`/`run_live_augment` 皆改 team scope；「顯示收錄人」：`captured_by_name` 串到 list/detail（前端 `ContactListCard`「👤 由 X 收錄」、`ContactDetailPage`「團隊共享」）。dogfood：同公司成員用相同 `seed_org` slug 登入即同一團隊。驗證：新增 `tests/test_a_team_pool.py`（同 org 共享、外人排除、無 org 退回單人）通過；全 90 passed / 1 failed（僅 pre-existing `test_m11...reindexes`）。註：早前為清 M11 stale-data 誤 TRUNCATE 掉手動種子 stub「Ting Hsieh」，已重建並 index_stub 還原，semantic_rescue 3 測試恢復。
- 2026-07-13：**實作 B 人工備註（順序 C→B→A 的第二塊）**。用戶澄清「特質/經歷/合作可能性」只是舉例、非硬規格；AI 能做的（公司 M6／職責 M3／合作切入點 C）大多已建，B 收斂為「加一個人工備註欄、AI 不碰」以避免編造。`Contact.personal_note`(migration `016_contact_personal_note`)＋`ContactUpdateFields`/`ContactDetailResponse`/patch field_map/`update_contact_fields`/`to_detail` 皆串接；前端 `ContactDetailPage` 新增可編輯「📝 我的備註」區(標「AI 不會動」)。驗證：全後端測試（排除 1 個 pre-existing M11 stale-data 失敗）85 passed；`test_m3_contact_update`＋`test_m5_precision` 12 passed；前端 lint 乾淨。註：跑測試需先 `alembic upgrade head`（DB 已升到 016）。已知 pre-existing 失敗 `test_m11_public_directory::test_m11_patch_published_reindexes`（reindex 重複鍵，與本次無關，stash 基準線同樣失敗）。
- 2026-07-13：**實作 C 商機簡報（v1 · 順序 C→B→A 的第一塊）**。後端：`RerankItem`＋rerank prompt(v5) 產出 `opening_line`(開場白)＋`collaboration_note`(合作切入點)；`SearchResult` 新增 `opening_line/collaboration_note/dormant_months` 欄（migration `015_search_briefing`）；`m5_search/service.py` 以名片收錄時間(created_at)為 proxy 計算「沉睡 N 月」(閾值 6 月)、合成 briefing 標題(翻過 N 張/對上 M 位/沉睡 K 位)、回 `BriefingDTO`，`get_search_query`/live-augment 皆帶回。前端：`SearchResultCard` 加沉睡 chip＋合作切入點＋「幫你想好的開場白」可複製區；`SearchPage` 加簡報標題 banner＋「其餘 N 張沒硬湊給你」誠實 footer。驗證：`py_compile` OK、前端 lint 乾淨、`tests/test_m5_search_flow.py`＋`test_m5_constraints.py` 8 passed。對應原型 `spec/screens/screen-1-opportunity-briefing.html`。dormant 待 A/後續換成真正 last_contacted_at。
- 2026-07-13：**決策：團隊共享池採「最小改法」（dogfood）**。單一 `team_id` 全公司共用，搜尋/列表過濾從 `user_id` 改 team scope，**不做**權限 UI／私有-共享旋鈕（推遲至 Phase 2 #8「公司政策旋鈕」、Phase 3 #12「多租戶」）。理由：dogfood 僅一家公司、避免重回「蓋完整系統」泥沼、且最小 `team_id` 可無痛升級成正式 org 模型。程式碼盤點見 [code inventory](e471a4e0-c5f0-41f3-a831-bf83545288f2)：M2 收錄/OCR、M3 職責、M5 對話搜尋、M6 看懂公司「已建可用」；缺「團隊池 tenancy」「dossier 三欄（特質/經歷/合作可能性，全新）」「商機簡報 UI（引擎有、體驗無）」。
- 2026-07-13：**用戶確認 v3 團隊工具方向（看原型後「對」）**。補充定調：① **Later 功能全部保留**（外部供應商發現池/對外版/收款/報表），非砍除，只**排先後**（Phase 1→2→3）；「都要 ≠ 一起做」。② **AI 為產品脊椎**（非配料）：每階段核心動作皆 AI（P1 自動 dossier + 反向找商機；P2 LinkedIn/上網查 + 開場白生成；P3 AI 外部供應商發現）。路線圖更新為「優先順序總圖」`spec/screens/roadmap-now-next-later.html`。下一步：盤現有 code → v1 dogfood 實作清單。
- 2026-07-13：**PRD v3 草案建立**（`BSChat_PRD_v3.md`）— 重定位團隊聯絡人情報工具、AI 自動 dossier 取代助理手工表格、名片可見＝兩層模型（跨公司絕對私密 + 公司內政策旋鈕，v1 預設共享不建權限 UI）、外部池/收款＝Later、驗證＝dogfood。DDR-v3-1~6。喜好/請客備註→v1.1。
- 2026-07-13：**產品形狀重大確認（A+C）= 團隊聯絡人情報工具 · dogfood 自家公司 → 對外**。使用者揭露真實處境：本身經營公司，底下有**業務團隊（含業務助理）＋採購**。業務助理**手工用表格**整理名片（特質/職稱/經歷/合作可能性/高階者喜好備註）；採購拿名片**拓展新合作商**，否則靠 Google。
  - **解消先前多個岔路**：
    - 「業務 vs 秘書/CRM」→ 在一個團隊裡是**同一池名片、不同角色使用**：業務助理的手工 dossier＝真實工時痛（**修正 7/9「park CRM」的判斷**，它是 v1 核心價值之一）；採購/業務找商機是另一半。
    - 「單邊 vs 雙邊」→ **v1＝團隊內部共享池（單邊、自家資料，無冷啟動）**；外部供應商發現池（雙邊/Pool B）留 Later。
    - 冷啟動問題**消失**：自家公司同時是第一個供給＋需求。
  - **v1 客戶＝自家公司團隊（dogfood）**；**願景＝對外賣給業務團隊/公司（C）**。
  - **重大反轉待 v3 處理**：舊 PRD「預設私密·單機」→ 新方向需要**團隊共享池**（衝擊 M7 隱私模型、DDR-59/62）。
  - 下一步：寫 **PRD v3**（scoped 到 dogfood v1）；驗證＝dogfood 自家團隊（看業務助理是否棄用手工表格、採購是否棄用 Google）。
- 2026-07-09：**歷史卡點排序（Now/Next/Later）** — 用戶指出專案先前卡在三件事，經診斷皆為「核心未驗證前的下游/擴張投入」，排序如下（`spec/screens/roadmap-now-next-later.html`）：
  - **Now（唯一焦點）**：驗證核心「商機簡報」拉力（真實業務）。核心引擎 M2/M3/M5/M6 已建，足以驗證。
  - **Next（核心驗證後）**：LinkedIn 串接（M3.5，核心增強；**別再卡官方 API**，已有 Gemini 公開搜尋 + card_inference 過渡）、live 查、簡報體驗打磨。
  - **Later（PMF 後）**：① **Solo 自創電子名片分享**＝第二產品/潛在成長迴圈，**違反 DDR-75**、有 cold-start 風險，需重新產品決策（非加功能）；② 運營後台 + 分級收款＝變現水管，驗證期 plan_tier hardcode 即可（DDR-39）；③ 企業 Pool B/M5b 凍結中。
- 2026-07-09：核心 App 其餘畫面原型 `spec/screens/screen-2-core-app-screens.html`（名片庫列表、聯絡人詳情 AI 透明三區、待確認延後最低確認、我的 Account Hub·Free）。刻意不含 e-card 自創/收款後台/企業 org（Later/凍結）。
- 2026-07-09：完整流程原型 `spec/screens/screen-flow-sales.html`（收錄→AI看懂公司→一句需求→商機簡報），供真實業務走查。persona 鎖定業務、CRM 劃出範圍外（見「已確認決策」2026-07-09）。
- 2026-07-09：**產品重審（pm-role 重審模式）** — 結論「先驗證核心再擴張」；凍結下游（Pool B/M5b/企業版）投入；產出殺手時刻畫面原型 `spec/screens/screen-1-opportunity-briefing.html`，待真實 B2B 業務驗證拉力後再定 PRD 是否大改。詳見「已確認決策」2026-07-09 條。
- 2026-06-30：**M5 dev search debug 面板** — `SearchQueryResponse.debug`（DEBUG 门控）；前端 `SearchDebugPanel`（development only）；设定页「AI 严格度」文案
- 2026-06-30：**M5 pgvector 混合召回** — migration 014、Gemini text-embedding-004（768d）、ts+trgm+vector RRF；Docker Postgres 改 `pgvector/pgvector:pg16`；`scripts/backfill_search_embeddings.py`
- 2026-06-17：**M5 检索契约 DDR-101** — 统一漏斗 spec；两种分数分工写入 PRD §11.9.1b、SA/SD M5 §2.6、ENG M5 §1.1、QA M5 §2.12
- 2026-06-16：**M5 PM/UIUX v1.2/v1.1** — 对齐 PRD v2.5 §11.8~9（Account Hub、搜尋精準度、Stage 1b、跨池 UX）
- 2026-06-16：**M5 搜尋 UX** — Pro 預設 `search_scope=all`；結果 badge + 結果頁篩選 chip
- 2026-06-16：**M5b 跨池搜尋** — Pro/Enterprise 可搜公開商務池（`search_scope` network/all）、公開結果卡（無電話/Email + 外部連結）。migration 012。73 tests
- 2026-06-16：**M11 MVP 實作** — migration 011、Admin API、Pool B index worker、dev seed（acme-demo）、Admin UI `/admin/org`、4 條 API 測試。下一棒 M5b
- 2026-06-16：**PRD §13 對焦 §11** — 移除舊第四檔加購敘事；跨池搜尋 = Pro 內建、企業版 = 發布公開目錄
- 2026-06-16：**M11 SA-SD v1.0 + PM L3** — org/stub/Pool B schema、Admin API、M5b 介面契約、DDR-90~95。下一棒 ENG 實作
- 2026-06-16：**M11 kickoff 通過**（Stage 2 主線）— 企業 Admin 發 stub → Pool B；MVP 切片鎖定（薄 stub + CSV + 索引；不做 billing/SSO/HR）。下一棒 SA/SD M11 + PM L3。見 `spec/kickoffs/m11-20260616.md`
- 2026-06-16：Media URL Policy — DB 存 `/uploads/...`；API 經 `public_media_url()` 依 `STORAGE_PUBLIC_BASE_URL` 回完整 URL；上線改 env 即可（TECH_STACK §7.3）（Pro 設定 PATCH/403、live-augment 扣額度 + query_augmentations + DDR-36 不寫 cache）61 passed
- 2026-06-16：Stage 1 開工 — **Pro 設定 UI**（`/settings`：方案、用量、auto-refresh、LinkedIn 自動補充）+ **M5 Layer3 live 查**（`POST /search/queries/:id/live-augment`、`query_augmentations` 表、`suggest_live` 觸發、扣 `live_augment` 額度、match_reason「即時查詢」標注；DDR-36 不寫 M6 cache）
- 2026-06-15：Pro 產品定位收斂 + 分階段（PRD §11.5 細化）。Free＝「讓交換名片變有價值」；Pro＝＋「推薦可合作的名片（平台公開商務身份）」。**Pro 靈魂「推薦合作」依賴 Pool B，而 Pool B 只能由企業 Admin 發布（DDR-76/77）→ 必須等企業帳號**。階段：Stage 0（已完成 Pro 自己庫價值）/ Stage 1（可獨立做：Layer3 live 查 + Pro 設定 UI + E2E）/ Stage 2（⏳ 等企業帳號：M11 Pool B → M5b 跨池推薦）。M11/M5b 於 register 標 blocked-by 企業帳號。
- 2026-06-11：M35-009 決策 — 官方 LinkedIn API **待審核未過，擱置**。Pro 上線資料來源僅靠：①有 URL → Gemini 公開搜尋（`linkedin_url_public`「○ 依連結公開摘要」）②無 URL → `card_inference`「○ 名片推估」。**mock/無官方 API 時永不輸出 ✦ LinkedIn**（紅旗 2 收斂為硬化 + 測試，非接 provider）。
- 2026-06-11：`sa-sd-role`（模組模式）更新 `SA-SD_M35` v1.1 對齊 data_source 6 類動態標籤（紅旗 1 解除，R-35.7 作廢），並補 `ENG_M35` v1.0（Python，對齊實際 code；DDR-86~88）。M3.5 剩紅旗 2（mock 防冒充＋接真 provider）為純實作工作。
- 2026-06-11：`pm-role` 拍板 M3.5 data_source 4+1 項決策（DDR-81~85），寫回 PRD §12.5.4、`BSChat_M35_data_source.md` §2/§3、module-register。M3.5 紅旗 3 解除；剩餘紅旗 1（SA-SD 對齊）轉 `sa-sd-role`、紅旗 2（mock 防冒充）為實作。
- 2026-06-11：`project-onboard` 重建狀態檔（project-context、module-register、onboarding report、根 AGENTS.md）。盤點發現 M3.5 為進行中模組（全部未提交），核心缺口 = `person_search_provider=mock` 仍輸出假資料、data_source 標籤未動態化、缺 M3.5 ENG spec。
- 🟡 待辦：PRD 雙版本並存（`BSChat_PRD.md` + `BSChat_PRD_v2.md`），建議合併為單一 `prd.md`（頂端標確認日期），舊版靠 git 歷史。尚未執行。
