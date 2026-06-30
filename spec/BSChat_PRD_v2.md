# BSChat PRD v2 — 訪談深化版

> **文件性質**：本文件為 `BSChat_PRD.md` 的補充與修正，基於 2026-05 使用者訪談產出。  
> **適用範圍**：MVP 設計、模組深化（SDLC Phase 1）的優先依據。  
> **原 PRD 狀態**：L1/L2 仍有效；本文件修正 L3 層的使用者情境、MVP 優先順序與設計原則。

---

## TL;DR（v2 修正）

原 PRD 將 BSChat 定位為「AI 驅動的名片管理與商務人脈平台」，方向正確，但**低估了核心使用情境的深度**。

v2 訪談揭示的真實需求是：

> **不是「存名片」，而是「要用時，從累積人脈中反向找出跟當下業務需求有關的潛在商機」。**

使用者不會整理名片、不會當下補備註、不會記得對話內容。產品必須適應這些行為現實，而非要求使用者改變習慣。

**MVP 核心從「名片 OCR + 搜尋」修正為「批次收錄 + 公司業務理解 + 對話式商機匹配」。**

---

## 1. 深化 Persona — Primary User

### 1.1 基本輪廓

| 欄位 | 描述 |
|------|------|
| 角色 | B2B 業務代表 |
| 名片來源 | 各種場合（展覽、拜訪、轉介紹、日常商務） |
| 名片形式 | 紙本 + LINE/Email 電子連結 + 展覽 QR code（三軌並行） |
| 管理方式 | 紙本放抽屜；電子連結留 LINE 聊天記錄；基本上不整理 |
| 後悔時機 | follow-up 時、老闆要名單時、自己找商機時 |
| 使用頻率 | **事件驅動，非固定週期**（「不一定」— 被需求觸發才需要搜尋） |

### 1.2 行為現實（Product Must Assume）

- **不會**在收名片當下補充備註或整理
- **不會**記得當下與對方聊了什麼、對方負責哪塊業務
- **不會**長時間投入 digitize 舊名片（最多 10 分鐘試用）
- **會**在需要時才後悔「當初沒好好整理」
- **會**先用 Google 查公司，再手動對照手中名片

### 1.3 核心需求（一句話）

> 用對話描述「我現在要找什麼」，從已收錄的名片庫中，反向找出公司對、人對的潛在商機，並能立刻聯絡。

### 1.4 「夠用」的判斷標準

看到一張名片（或聯絡人）時，使用者認為「有用了」的最低資訊：

1. **這家公司主要產品是什麼**（AI 從公開資料補全）
2. **這個人負責哪一塊業務**（AI 從職稱 + 公司資訊推估，標示不確定）

判斷邏輯：

```
公司對 + 人對 = 值得 follow-up
只有一個對     = 可能還要再查
兩個都不清楚   = 直接放棄
```

### 1.5 痛點鏈（完整）

```
知道要找什麼類型（商機需求）
    ↓
① 想不起來有沒有收過這類名片
    ↓
② 就算有，公司名稱也看不出做什麼  ← 【最常放棄的引爆點】
    ↓
③ 就算記得，實體名片可能已經找不到
    ↓
④ 就算找到了，也不確定是不是同一家公司
    ↓
最終：放棄，或花很多時間勉強湊
```

---

## 2. Scenario Library（場景庫）

### S-01：Google 研究後對名片

| 項目 | 內容 |
|------|------|
| **觸發** | 自己或老闆提出某類商機需求（例如：「有沒有認識做工業電腦的？」） |
| **現有流程** | Google 查公司類型 → 心裡形成條件 → 翻抽屜 / 回想名片 → 常對不上 |
| **挫折點** | 名片看不出公司做什麼；想不起來有沒有收過；找到了也不確定 |
| **理想流程** | 直接問 BSChat：「我手上有誰是做 XXX 的？」→ 得到排序清單 + 匹配理由 |
| **關鍵能力** | M5 對話式搜尋 + M6 公司產品補全 + M3 個人職責推估 |
| **成功標準** | 從「開始搜尋」到「找到可聯絡對象」< 2 分鐘 |

### S-02：展覽批次連拍

| 項目 | 內容 |
|------|------|
| **觸發** | 展覽 / 會議現場收到大量紙本名片 |
| **現有流程** | 塞口袋 → 回家放抽屜 → 不再整理 |
| **挫折點** | 當下沒時間整理；之後想 follow-up 時全部忘光 |
| **理想流程** | 打開 App → 連拍模式一次拍很多張 → 當下零必填 → 背景 OCR + 公司補全 |
| **延後確認** | 之後有空時，快速滑過只確認「姓名 / 公司」對不對，其他不管 |
| **關鍵能力** | M2 批次連拍 + 背景 OCR + 獨立狀態（部分失敗不影響其他） |
| **成功標準** | 單張收錄操作 < 3 秒（拍照即完成） |

### S-03：電子名片留在 LINE

| 項目 | 內容 |
|------|------|
| **觸發** | 對方透過 LINE / Email 傳送電子名片連結 |
| **現有流程** | 連結留在聊天記錄 → 等於沒收 → 之後找不到 |
| **根本原因** | 不知道怎麼「收」，更不知道「收了之後能幹嘛」 |
| **理想流程 A** | 複製連結 → 貼到 BSChat → 自動解析 → 進名片庫 |
| **理想流程 B** | 展覽現場掃 QR code → 直接進 BSChat |
| **關鍵能力** | M2 URL 解析匯入 + M2 QR 掃描匯入 |
| **成功標準** | 從收到連結到收錄完成 < 10 秒 |

### S-04：找到人後立刻聯絡

| 項目 | 內容 |
|------|------|
| **觸發** | AI 搜尋找到符合條件的聯絡人 |
| **現有流程** | 還要再找電話 / Email → 切換到其他 App 聯絡 |
| **理想流程** | 一鍵複製電話/Email，或 App 內直接發送 |
| **關鍵能力** | M8 匯出與行動（複製 P0；App 內發送 P1） |
| **成功標準** | 從「看到搜尋結果」到「開始聯絡」< 10 秒 |

---

## 3. Negative Scenarios（失敗 / 放棄情境）

| ID | 情境 | 使用者行為 | 產品後果 | 設計對策 |
|----|------|-----------|---------|---------|
| N-01 | 名片看不出公司做什麼 | **直接放棄搜尋** | 產品無價值 | M6 必須補「主要產品」，且為 P0 |
| N-02 | 想不起來有沒有收過這類名片 | 放棄 | 資料未 digitize | 降低收錄門檻；10 分鐘內看到 aha moment |
| N-03 | 實體名片物理遺失 | 即使有印象也無用 | — | 掃描後留存數位副本 |
| N-04 | AI 推估個人負責業務常錯 | **停用產品** | 信任崩潰 | 低信心不推估；標示來源與不確定 |
| N-05 | AI 補全公司產品常錯 | 不再信任搜尋結果 | 核心價值失效 | 顯示資料來源；允許使用者拒絕/覆寫 |
| N-06 | 收錄流程太複雜（>10 分鐘） | onboarding 放棄 | 無資料可搜 | 連拍零必填；延後最低確認 |
| N-07 | 要求當場補備註 / 分類 | 使用者不做 | 資料品質差 | 不要求；AI 自動補 |
| N-08 | 固定業務方向設定過期 | 設定無效 | 搜尋結果偏離 | 對話式即時意圖，不固定儲存 profile；**搜尋精準度偏好**除外（見 DDR-96~100） |

---

## 4. 訪談決策紀錄（DDR）

| ID | 決策 | 理由 | 影響模組 |
|----|------|------|---------|
| DDR-5 | 業務方向採「對話式、即時意圖」，不固定儲存 profile | B2B 業務方向隨公司政策頻繁變動 | M5 搜尋、Onboarding |
| DDR-6 | MVP 第一價值 =「看懂公司」+「反向找商機」 | 使用者放棄主因是看不懂公司做什麼 | M5、M6 |
| DDR-7 | 名片「夠用」最低標準 = 公司主要產品 + 個人負責業務 | 使用者明確表述的判斷標準 | M3、M5、M6 |
| DDR-8 | 「個人負責業務」採 AI 推估，不要求使用者當場補充 | 名片都會不見，不可能保留當下對話記憶 | M3、M6 |
| DDR-9 | AI 推估可接受，但「常錯」= 流失 | 使用者選 B（勉強可接受，常錯不用） | M5、M6 UI |
| DDR-10 | 舊名片 digitize 意願 = 10 分鐘試用級 | 不會為「也許以後有用」花半下午 | M2 onboarding |
| DDR-11 | 收錄 UX = 批次連拍 + 延後只確認姓名/公司 | 使用者明確描述的「簡單」定義 | M2、M3 |
| DDR-12 | 電子名片來源 = LINE/Email 連結 + 展覽 QR | 使用者 A+B 都有遇到 | M2 |
| DDR-13 | 電子名片痛點 = 不知道如何收取與應用 | 連結留聊天記錄 = 未收錄 | M2 UX 文案 |
| DDR-14 | 電子名片匯入 MVP = 貼連結 + 掃 QR | 使用者接受 A or C，不需 LINE 原生分享 | M2 |
| DDR-15 | 找到人後核心行動 = 立即聯絡（複製 or App 內） | 不做 CRM pipeline | M8 |
| DDR-33 | MVP 不追蹤人員在職狀態 | 名片為交換當下快照，非 HR 系統 | M3、M6 |
| DDR-34 | 公司資料採 Cache-at-ingest + Query-time 混合 | 收錄時快取（M6）+ 搜尋時 live 查（M5） | M5、M6 |
| DDR-35 | enrich 結果必須帶 `enriched_at` | UI 顯示「公司資訊 · 更新於 …」 | M6 |
| DDR-36 | M5 live 查不自動覆寫 M6 cache | 除非使用者「採用本次查詢結果」 | M5、M6 |
| DDR-58 | 搜尋分 Pool A（私人）/ Pool B（授权公开）；MVP 仅 A | Phase 3 跨池 | M5、M11 |
| DDR-59 | 禁止搜他人私人收錄聯絡人 | 只搜自愿公开商務身份 | M5、M7、M11 |
| DDR-60 | 企业电子名片 + 企业订阅 → Pool B 主路径 | 双边收费供给端 | M11、M1 |
| DDR-37 | 過期自動 refresh 為 **Pro** 功能 | Free 僅收錄時 enrich + 有限手動更新 | M1、M6 |
| DDR-38 | M1 管訂閱與開關；M6 管 enrich 執行 | 職責分離 | M1、M6 |
| DDR-39 | MVP 可 hardcode plan=free | schema 預留 Pro entitlement 欄位 | M1 |
| DDR-71 | MVP **不顯示**通用搜尋靈感 chips；**Pro** 才提供依已索引名片推導的個人化範例查詢 | 通用範例與使用者名片池無關、易誤觸消耗額度；個人化建議需有資料基礎才有價值；仍不固定儲存 profile（延續 DDR-5） | M5 搜尋、M1 訂閱 |
| DDR-72 | **UI 只顯示 Pool A「可搜尋」人數**；`indexed_count` 限指**自己名片庫已建索引**且**刪除同步遞減**；Pool B / 非自己庫的 AI 推薦來源**不共用「已索引」文案**，Pro/Phase 3 另列「商務網絡」或結果 `source_pool` | 避免「已索引 vs 聯絡人總數」雙數字混淆；為 Pro 搜公開商務池 / 庫外推薦預留語意 | M5、M3、M11、M1 |
| DDR-73 | 對話式搜尋解析**多維度查詢條件**（公司/產業/場合/職能/地區等），**不限於職稱字面**；使用者明確約束（如「架構師就好」）視為**硬條件**，跨欄位比對（`title`、`responsibility_scope`、`company_products`、`company_name`、`source_label` 等），**不符合則不返回**；禁止 `match_reason` 寫「不符合」卻仍出現在結果中 | 使用者用產業/公司/情境問法多樣；召回+rerank 易「部分相關就列出」；硬條件寧可 NO_MATCH（延續 DDR-5） | M5 搜尋、M3、M6 |
| DDR-74 | **個人職責理解分層**：Free = M3 LLM 推估（title + company + M6 products）；Pro/Enterprise = 可加 **M3.5 LinkedIn + LLM** 個人公開資料補充；Free **永不**觸發外部 people search | 持續 API 成本與錯人風險應付費；Free 仍保留 Aha（公司 + 推估）；LinkedIn 資料經第三方/API，非 M6 公司 enrich | M3、M3.5、M1 |
| DDR-75 | M3.5 **不自動對全庫 silent 搜人**；僅：① 名片/import 含 `linkedin_url` 且 Pro ② 使用者手動「LinkedIn 補充」③ Enterprise 可配置 batch（Phase 2）；`match_score < 0.8` 不寫入 Contact | 同名消歧與合規；寧可提示確認也不錯人寫庫 | M3.5、M1 |
| DDR-76 | M3.5 成功結果 **不覆寫** OCR `title`；寫入 `person_responsibility_scope`（或增強 `responsibility_scope`）並標 `provenance=linkedin`；M5 硬匹配需 `person_match_score ≥ 0.8` 且 confidence ≥ 0.75 | 名片為交換快照；LinkedIn 為補充視角 | M3.5、M5、M3 |
| DDR-96 | **「我的」為三方案共用 Account Hub**（`/settings` 或 App「我的」Tab）；依 `plan_tier` **顯示/隱藏區塊**，非三套獨立 App | 設定集中、方案差異可見；避免 Free 無入口 | M1、UI |
| DDR-97 | **搜尋精準度**（strict / balanced / exploratory）為**搜尋嚴格度偏好**，可持久化於使用者設定；**不等於**業務方向 profile（延續 DDR-5） | 使用者需控制「要多準 vs 多給可能」；與對話式即時意團並存 | M5、M1 |
| DDR-98 | **Free 開放「精準 + 平衡」**；**「探索」鎖 Pro+**（UI 可預覽 + 升級 CTA）；**自訂分數 / 組織預設**鎖企業版 Admin（P2） | 兼顧留存（Free 可調基本精準度）與付費誘因（放寬匹配 + 跨池在同一價值線） | M1、M5 |
| DDR-99 | **禁止 retrieval fallback 湊數**（如模板「文字相關」+ 固定 0.35 分硬塞 results）；`match_score` **不得**作為服务端 EMPTY 的硬門檻（見 DDR-101）；LLM 離線（`degraded`）時寧可 EMPTY + 說明，不硬塞假結果 | 消除「模糊比對感」；信任 > 湊數 | M5 |
| DDR-100 | 搜尋結果 UI 必須展示 **match_sources chips**；`degraded=true` 時明顯標「簡化模式／結果僅供參考」 | 讓 AI 感可感知、降級可解釋 | M5 UI |
| DDR-101 | **M5 统一检索漏斗**（全用户、全池规模同一 pipeline）：① LLM 精炼 intent → ② DB 混合召回 top-K（固定 `RETRIEVAL_TOP_K`，禁止按名片库大小分叉）→ ③ LLM rerank → ④ 后端只守边界（权限、hard constraint、schema 校验）。**两种分数分工**：`retrieval_score` 仅用于召回池内排序/合并；`match_score` 仅用于 rerank 后排序、展示、日志/QA——**均不得**单独决定「有没有结果」。`search_precision` 注入 rerank prompt，**不**映射 `min_match_score` 过滤 | 问法再怪仍由 AI 理解；行为可量化、可复测 | M5 |

---

## 5. MVP 功能優先順序（v2 修正）

### 5.1 原 PRD vs v2 修正

| 原 PRD 假設 | v2 修正 |
|------------|---------|
| 核心流程 = 掃描 → OCR → 審核 → 搜尋 | 核心流程 = **連拍收錄 → AI 理解公司 → 對話式找商機** |
| AI 搜尋是管理層功能之一 | AI 搜尋 + 公司補全是 **MVP 核心價值** |
| 使用者會在 review 階段編輯確認 | 延後最低確認（只確認姓名/公司） |
| onboarding 引導上傳 10-20 筆 | 掃 3-5 張 → 立刻試搜 → aha moment → 才繼續 |
| 公司補全 P1 | 公司主要產品補全 **提升為 P0** |

### 5.2 修正後優先順序

| 優先 | 模組 | 能力 | 依據 |
|------|------|------|------|
| **P0** | M2 | 批次連拍 + 延後最低確認 | DDR-11 |
| **P0** | M2 | 背景 OCR（不要求當場確認） | S-02 |
| **P0** | M6 | 公司主要產品 AI 補全 + 來源/信心標示 | DDR-6, DDR-7 |
| **P0** | M5 | 對話式反向搜尋（「我手上有誰做 XXX？」） | S-01 |
| **P0** | M3 | 個人負責業務 AI 推估（標示不確定） | DDR-8, DDR-9 · `BSChat_PM_M3.md` |
| **P0** | M7 | 預設私密 + 刪除支援 | 原 PRD P0 |
| **P1** | M2 | 貼連結匯入電子名片 | DDR-14, S-03 |
| **P1** | M2 | 掃 QR 匯入電子名片 | DDR-14, S-03 |
| **P1** | M8 | 找到後一鍵複製 / App 內聯絡 | DDR-15, S-04 |
| **P1** | M4 | 重複偵測（Email/電話比對） | 原 PRD P0 |
| **P2** | M8 | CSV 匯出給老闆 | 使用者未選此需求 |
| **P2** | M1 | 完整帳號/團隊 workspace | 原 PRD Phase 後 |
| **P3** | M11 | 企業電子名片 + 授權公開商務池（AI 可搜） | §13、DDR-58~62 |
| **P3** | M5b | 跨池搜尋（私人池 + 公開池） | §13 |

---

## 6. 修正後 User Stories（Primary Persona）

### Module: 名片收錄（M2）

**US-2.1 批次連拍**
> As a B2B 業務代表, I want to 在展覽現場連拍多張名片, so that 我可以在 10 分鐘內快速收錄而不需要當場整理。

Acceptance Criteria:
- Given 我在展覽現場, When 我開啟連拍模式並連續拍照, Then 每張照片自動上傳並排入 OCR 佇列，我無需填寫任何欄位
- Given 連拍中某張 OCR 失敗, When 其他張仍在處理, Then 失敗的不影響成功的，且失敗項標記待確認
- Given 我拍完 5 張, When 我離開 App, Then 背景繼續 OCR + 公司補全，我下次打開可看到結果

**US-2.2 延後最低確認**
> As a B2B 業務代表, I want to 之後只快速確認姓名和公司是否正確, so that 我不需要在收名片當下花時間整理。

Acceptance Criteria:
- Given OCR 完成, When 我進入待確認列表, Then 我只需檢查姓名/公司，其他欄位已由 AI 處理
- Given 某筆信心度低, When 我滑過未確認, Then 系統標記「待確認」但不阻擋搜尋

**US-2.3 電子名片貼連結**
> As a B2B 業務代表, I want to 複製 LINE 上的電子名片連結貼到 BSChat, so that 電子名片不會再留在聊天記錄裡消失。

**US-2.4 展覽 QR 掃描**
> As a B2B 業務代表, I want to 掃描對方的 QR code 直接收進 BSChat, so that 電子名片跟紙本名片在同一個地方。

### Module: AI 搜尋（M5）

**US-5.1 對話式找商機**
> As a B2B 業務代表, I want to 用自然語言問「我手上有誰做工業電腦的？」, so that 我不需要記得精確姓名或公司名也能找到潛在商機。

Acceptance Criteria:
- Given 我的名片庫有 20+ 筆, When 我輸入「我手上有誰做 IPC 的？」, Then 回傳排序結果 + 每位匹配理由（基於公司產品/個人職責）
- Given 我的業務方向這季改變, When 我輸入新的搜尋意圖, Then 不需要修改任何 profile 設定

**US-5.2 搜尋結果解釋**
> As a B2B 業務代表, I want to 看到系統為何回傳某個結果, so that 我能判斷是否值得 follow-up。

Acceptance Criteria:
- Given 搜尋回傳 3 筆結果, When 我查看任一結果, Then 顯示匹配理由（例如：「公司主要產品包含工業電腦主機；此人職稱為 OEM 業務經理（AI 推估）」）
- Given 結果含結構化依據, When 我查看結果卡, Then 顯示 **match_sources** 欄位 chip（職稱、公司產品、職責推估等 · DDR-100）

**US-5.3 搜尋精準度偏好（Account Hub）**
> As a B2B 業務代表, I want to 在「我的」設定搜尋要多精準, so that 我可以自己決定結果要嚴格還是寬鬆，而不必每次換問法試運氣。

Acceptance Criteria:
- Given Free 使用者, When 進入「我的 → 搜尋偏好」, Then 可選 **精準** 或 **平衡**；**探索**顯示鎖定 + Pro 升級說明（DDR-98）
- Given Pro 使用者, When 選 **探索**, Then 搜尋允許較低 `match_score` 門檻（仍禁止低分 fallback 模板結果 · DDR-99）
- Given 使用者選 **精準**, When 無人達門檻, Then 回傳 EMPTY + 建議放寬精準度或換問法（不硬塞無關結果）
- Given `degraded=true`（LLM 離線）, When 搜尋, Then UI 標「簡化模式」；fallback 分数仅供参考，不硬塞模板结果（DDR-99、DDR-101）
- Given 使用者變更精準度, When 儲存, Then 寫入 `user_settings.search_precision`；**不**寫入業務方向 profile（DDR-5、DDR-97）

**US-1.4 帳號／我的（Account Hub）**
> As a 使用者（Free / Pro / 企業版）, I want to 在同一個「我的」入口看到帳號資訊與方案相符的設定, so that 我知道自己能調什麼、升級能解鎖什麼。

Acceptance Criteria:
- Given 任一方案, When 進入「我的」, Then 顯示：帳號摘要、方案 badge、本期用量、**搜尋偏好**、資料與隱私說明（§11.8）
- Given Pro, When 進入「我的」, Then 另顯示資料更新區（auto refresh、LinkedIn 自動補充 · 現行 Stage 1）
- Given 企業版, When 進入「我的」, Then 另顯示組織摘要 + 連結「公開目錄管理」（`/admin/org`）；不與 Pro 個人設定混在同一表單區塊
- Given Free, When 查看 Pro 鎖定區塊, Then 區塊可見但 disabled + 升級 CTA（非完全隱藏搜尋偏好）

### Module: 公司資訊補全（M6）

**US-6.1 公司主要產品補全**
> As a B2B 業務代表, I want to 看到每家公司主要產品是什麼, so that 我可以判斷這張名片值不值得繼續看。

Acceptance Criteria:
- Given 名片 OCR 完成, When 背景補全執行, Then 自動填入「主要產品/服務」並標示資料來源與信心度
- Given AI 信心度 < 0.5, When 顯示在 UI, Then 顯示「資訊不足」而非錯誤猜測

**US-6.2 個人負責業務推估**
> As a B2B 業務代表, I want to 看到 AI 推估這個人可能負責哪塊業務, so that 即使我當初沒有記下來，仍能判斷是否為正確窗口。

Acceptance Criteria:
- Given 職稱為「業務經理」且公司已補全產品資訊, When 顯示聯絡人, Then 顯示 AI 推估的負責範圍 + 「AI 推估，不確定」標示
- Given AI 推估信心度低, When 顯示, Then 不顯示推估（寧可空白不要錯）

### Module: 匯出與行動（M8）

**US-8.1 找到後立刻聯絡**
> As a B2B 業務代表, I want to 在搜尋結果中一鍵複製電話或 Email, so that 我可以立刻用習慣的方式聯絡對方。

---

## 7. 修正後 Onboarding 流程

原 PRD：引導上傳 10-20 筆 → 強調三層價值 → 隱私說明

**v2 修正：Aha Moment First**

```
Step 1: 極簡註冊（Email / 手機，無業務方向設定）
Step 2: 「試試看」— 引導連拍 3 張名片（或貼 1 個連結）
Step 3: 背景處理（OCR + 公司補全，顯示進度但不阻塞）
Step 4: 「現在試試看」— 引導第一次對話式搜尋
        例如：「我手上有誰做 [產業] 的？」
Step 5: 看到結果 + 匹配理由 → Aha Moment
Step 6: 「繼續收錄更多名片，搜尋會更準」→ 引導繼續掃描
Step 7: 隱私說明（簡短，非阻塞）
```

**關鍵指標**：
- 從註冊到第一次搜尋 < 10 分鐘
- 第一次搜尋有結果 = aha moment
- 有 aha moment 的使用者才會繼續 digitize 更多名片

---

## 8. 修正後 Success Metrics

### 新增 / 修正指標

| 指標 | 定義 | MVP 目標 | 依據 |
|------|------|---------|------|
| Aha Moment Rate | 首次搜尋有 ≥1 結果的用戶比例 | > 60% | DDR-10 |
| 收錄完成率（10 分鐘內） | 10 分鐘內成功收錄 ≥3 張的用戶比例 | > 70% | DDR-10, DDR-11 |
| 公司產品補全可用率 | 補全後使用者未拒絕/覆寫的比例 | > 75% | DDR-9 |
| 搜尋後聯絡率 | 搜尋結果中被複製/聯絡的比例 | > 30% | S-04 |
| AI 推估信任度 | 使用者對 AI 推估結果的滿意度（主觀） | > 3.5/5 | DDR-9 |
| 收錄操作時間 | 單張名片從拍照到完成上傳 | < 3 秒 | S-02 |

---

## 9. 對原 PRD 各層的影響摘要

| 原 PRD 章節 | v2 修正 |
|------------|---------|
| User Stories | 新增 Primary Persona 深化版 + 4 個場景故事 |
| Functional Requirements — 名片交換層 | 強調批次連拍 + 電子名片匯入 |
| Functional Requirements — AI 管理層 | 提升為 MVP 核心；搜尋意圖改為「找商機」 |
| Functional Requirements — 公司資訊補全層 | P1 → **P0**；必須含「主要產品」 |
| User Experience — Entry Point | 改為 Aha Moment First onboarding |
| User Experience — Core Experience | Step 1 改為連拍零必填；Step 2 延後最低確認 |
| Technical Considerations | 新增 AI 推估信心度門檻；新增 URL/QR 解析 |
| Milestones | Phase 1 應包含 M5/M6 最小可用版本，非只做收錄 |

---

## 10. 待後續模組深化時驗證的 🚧

以下項目在訪談中未完全確認，需在 SDLC Phase 1 模組深化時逐一鎖定：

| 🚧 | 議題 | 建議處理模組 |
|----|------|------------|
| B-1 | OCR 引擎選型（LLM-first vs 傳統 OCR + LLM 後處理） | M2 → SA/SD |
| B-2 | AI 推估「個人負責業務」的 prompt / 模型策略 | M3/M6 → SA/SD |
| B-3 | 公司產品補全的資料來源與成本上限 | M6 → SA/SD + ENG |
| B-4 | 10 分鐘 onboarding 的 aha moment 最低名片數 | M2/M5 → PM + ENG |
| B-5 | 電子名片 URL 解析的格式支援範圍 | M2 → SA/SD |
| B-8 | stale scheduler + M1 entitlement 接口 | M6 + M1 |

---

## 11. 商業模式與付費分層（v2.5 · 2026-06-16 鎖定）

> **取代** v2.1–v2.3 的 §11.2.1–§11.2.3、§11.4–§11.5 及舊版獨立加購方案敘事。  
> **對外只談三方案**：**Free｜Pro｜企業版**。§13 為 Phase 3 技術背景，方案分層以本章為準。

### 11.1 定價原則

> **Free 解決「當時看懂、找得到自己收過的人」；Pro 解決「資料長期準確 + 搜到平台公開商務身份」；企業版解決「團隊 + 對外可被找到的官方目錄」。**

- 不鎖定 **第一次 enrich** 或 **搜尋自己名片庫** —— 保留 Aha Moment
- 持續 API 成本（LinkedIn 補充、auto refresh、live 查、公開索引）→ 付費合理
- **產品紅線**：使用者收進抽屜的**私人聯絡人**永遠不可被其他使用者搜尋；可被搜尋的僅 **企業版 Admin 發布且預設公開的商務身份 stub**（DDR-76）

**平台定位（DDR-75）**：BSChat **不做完整電子名片宿主**；維護 **薄商務身份 stub**（姓名、公司、職稱、職責關鍵字）+ **外部名片 URL**（HiBox、官網、LinkedIn 等），供 AI 索引與導流。

**實作備註（不對外）**：後端索引可區分 `private_rolodex` / `public_directory`；**不作為售價維度或 UI 文案**。

### 11.2 三方案一句話

| 方案 | 對象 | 一句話 |
|------|------|--------|
| **Free** | 個人 | 收名片、AI 懂公司、搜**自己收錄**的聯絡人 |
| **Pro** | 個人 | Free + 職責/公司常更新 + 搜**平台公開商務身份**（摘要 + 外链） |
| **企業版** | B2B 團隊 | Pro × seat + **發布/管理**公司公開商務目錄（seat 預設公開） |

*Quota 數字均為 **Pilot TBD**；MVP 可先 hardcode，`plan_tier: free | pro | enterprise` 預留。*

### 11.3 能力總對照

#### 名詞：「手動更新公司資訊」（M6 · 非 LinkedIn）

聯絡人詳情 **「公司補全」→「更新公司資訊」**：重新抓取官網 + LLM，更新 `main_products`。

| 機制 | 觸發 | 更新對象 |
|------|------|----------|
| 收錄時 enrich（Layer 1） | 收名片後自動 | 公司產品 |
| 手動更新公司（M6） | 使用者按鈕 | 公司產品 |
| 過期自動 refresh（Layer 2） | 背景排程 | 公司產品（**Pro+**） |
| M3.5 LinkedIn 補充 | 按鈕 / URL 自動 | **個人**職責（**Pro+**，獨立 quota） |

#### A. 收錄與私人名片庫（M2 / M3 / M7）

| 能力 | Free | Pro | 企業版 |
|------|:----:|:---:|:------:|
| 連拍 / QR / 貼連結收錄 | ✅ | ✅ | ✅ |
| 背景 OCR + 待確認 | ✅ | ✅ | ✅ |
| 名片庫列表 / 詳情 / 編輯 / 刪除 | ✅ | ✅ | ✅ |
| 預設私密（僅本人可見） | ✅ | ✅ | ✅ |
| 儲存 `linkedin_url`（Free 不抓取） | ✅ | ✅ | ✅ |

#### B. 公司理解（M6）

| 能力 | Free | Pro | 企業版 |
|------|:----:|:---:|:------:|
| 收錄時公司 enrich | ✅ | ✅ | ✅ |
| 接受 / 拒絕 / 覆寫 AI 補全 | ✅ | ✅ | ✅ |
| 手動「更新公司資訊」 | ✅ **3/月** ※ | ✅ **50/月** ※ | ✅ **100/月** ※ |
| 過期自動 refresh | ❌ | ✅ | ✅ |
| 團隊共用 refresh 策略 | ❌ | ❌ | ✅ |

#### C. 個人職責（M3 + M3.5）

| 能力 | Free | Pro | 企業版 |
|------|:----:|:---:|:------:|
| M3 LLM 推估（title + company + products） | ✅ | ✅ | ✅ |
| M3.5 LinkedIn / 公開摘要補充 | ❌ | ✅ | ✅ |
| 名片含 LinkedIn → 背景自動 M3.5 | ❌ | ✅ | ✅ |
| 手動「從 LinkedIn 更新」 | ❌ | ✅ **20/月** ※ | ✅ **100/月** ※ |
| URL 自動 M3.5 占 manual quota | — | **不占** | **不占** |
| 全庫 batch person enrich | ❌ | ❌ | ✅ Admin opt-in |

**Free UX**：M3 推估 + Pro 升級 CTA；不呼叫 M3.5 API。

#### D. AI 搜尋（M5）

| 能力 | Free | Pro | 企業版 |
|------|:----:|:---:|:------:|
| 搜尋**自己收錄**的聯絡人 | ✅ | ✅ | ✅ |
| 搜尋**平台公開商務身份** | ❌ | ✅ | ✅ |
| 對話式自然語言搜尋 | ✅ | ✅ | ✅ |
| search_cache 每日額度 | **30/日** ※ | **50/日** ※ | **100/日** ※ |
| 個人化搜尋建議 chips | ❌ | ✅ | ✅ |
| live 上網查（公司 Layer 3） | **5/月** ※ | **30/月** ※ | **100/月** ※ |
| **搜尋精準度：精準 / 平衡** | ✅ | ✅ | ✅ |
| **搜尋精準度：探索** | 🔒 可預覽 | ✅ | ✅ |
| **自訂 match 分數門檻** | ❌ | ❌ | ✅ Admin 組織預設（P2） |
| 結果 **match_sources** chips | ✅ | ✅ | ✅ |
| 低分 **fallback 硬塞結果** | ❌ 全方案禁止（DDR-99） | ❌ | ❌ |

**公開搜尋結果 UX（DDR-80 · C1）**：只顯示摘要 + 標籤「公開商務 · {公司}」+ **「前往外部名片」**；**不在 BSChat 顯示電話/Email**。

**結果來源標示**：「你的名片庫」vs「公開商務 · {公司}」。

**搜尋精準度（§11.9）**：使用者於「我的 → 搜尋偏好」設定；**非**業務方向 profile（DDR-97）。

#### E. 公開商務目錄（M11 概念 · 企業版開發時實作）

| 能力 | Free | Pro | 企業版 |
|------|:----:|:---:|:------:|
| 出現在平台公開搜尋 | ❌ | ❌ | ✅ **seat 預設公開**（DDR-77） |
| Admin 設為不公開 / 下架 | — | — | ✅ **手動**（DDR-78；離職不自動下架） |
| 管理 org 成員、stub、外部 URL | — | — | ✅ |
| 名單匯入 / HR / SSO 串接 | — | — | 🚧 **企業版 kickoff 再定**（DDR-79；MVP 至少 Admin 手動 + CSV） |

**公開 stub 最小欄位**：姓名、公司、職稱、職責/產品關鍵字、**外部名片 URL（必填）**。不存電話/Email 供 Pro 結果展示。

#### F. 團隊與治理

| 能力 | Free | Pro | 企業版 |
|------|:----:|:---:|:------:|
| 單人使用 | ✅ | ✅ | 多 seat |
| 集中帳單 / seat 管理 | ❌ | ❌ | ✅ |
| 用量與公開曝光報表 | ❌ | ❌ | ✅ |
| audit log | ❌ | ❌ | ✅ P2 |

#### G. 帳號／我的（Account Hub · 入口能力）

| 能力 | Free | Pro | 企業版 |
|------|:----:|:---:|:------:|
| 「我的」統一入口（`/settings` 或 App Tab） | ✅ | ✅ | ✅ |
| 帳號摘要（email、顯示名、方案 badge） | ✅ | ✅ | ✅ |
| 本期用量（搜尋、live 查、M6/M3.5 quota） | ✅ | ✅ | ✅ |
| **搜尋偏好**（精準度 · §11.9） | ✅ 部分 | ✅ | ✅ |
| 資料與隱私（私密說明、Privacy Strip 連結） | ✅ | ✅ | ✅ |
| 資料更新（auto refresh、LinkedIn 自動補充） | 🔒 預覽 | ✅ | ✅ |
| 組織摘要 + 公開目錄 Admin 入口 | ❌ | ❌ | ✅ |
| 組織級搜尋預設精準度（Admin） | ❌ | ❌ | 🚧 P2 |

> 詳細 IA 與區塊順序見 **§11.8**。企業 **Admin 操作**（stub CRUD）在 `/admin/org`，與個人「我的」分路由，同一方案下兩者並存。

#### H. 行銷用一句對照

| | Free | Pro | 企業版 |
|---|------|-----|--------|
| **賣點** | 收錄即懂公司，搜自己庫 | 資料更準 + 搜公開商務窗口 | 團隊 Pro + 官方目錄被找到 |
| **不賣** | LinkedIn 補充、公開池、auto refresh | 發布/管理公開目錄 | — |

### 11.4 兩種資料生命週期（換工作）

| 資料 | 誰建立 | 誰能搜 | 對方換工作 |
|------|--------|--------|------------|
| **私人庫聯絡人** | 我掃描/匯入 | 僅我自己 | 維持**交換快照**；可选手動/M3.5 更新（DDR-33：不追蹤在職） |
| **公開商務身份** | 企業 Admin | Pro+ 全平台 | Admin **手動下架/更新**；外部名片 URL 指向現役平台 |

### 11.5 實施階段（2026-06-15 細化：分階段 + 企業依賴標注）

**產品定位收斂（2026-06-15）**：
- **Free**：讓交換名片變得有價值（收錄即懂公司、找回自己收過的人）。
- **Pro**：以上 ＋ **「推薦可合作的名片」**（從平台**公開商務身份**池找出潛在合作對象）。
- ⚠️ **關鍵依賴**：「推薦合作的名片」依賴 **Pool B（平台公開商務身份）**，而 Pool B **只能由企業版 Admin 發布員工 stub 產生**（DDR-76/77）。故 Pro 此賣點**必須等企業帳號出來且有客戶發布後**才能做到。

| 階段 | 方案 | 內容 | 企業依賴 |
|------|------|------|:--:|
| **Stage 0（已完成）** | Pro 自己庫價值 | M3.5 個人 LinkedIn 補充、M6 Layer2 過期自動 refresh、手動更新/搜尋額度、Pro 搜尋建議 chips | 否 |
| **Stage 1（Now／可獨立做）** | Pro「資料持續準確」完成式 | **M5+M6 Layer3 即時上網查**、**Pro 設定 UI**、Pro E2E 驗證（API 整合測試 ✅） | 否 |
| **Stage 1b（Next）** | 搜尋可信度 + Account Hub | **M5 1a/1b**（關 fallback、match_sources UI）、**§11.8 我的**、**§11.9 搜尋精準度分級** | 否 |
| **Stage 2（⏳ 等企業帳號）** | Pro 靈魂「推薦合作的名片」 | **M11**（企業 Admin 發布 stub → 建立 **Pool B**）→ **M5b**（Pool A+B 跨池搜尋/推薦） | **是** |

> **依賴鏈**：`企業版 M11 上線且有企業客戶發布 stub` → 有 Pool B → Pro「搜公開商務身份／推薦合作」（M5b）才成立。
> **MVP 現狀**：Pro 可交付範圍 = Stage 0+1（自己庫，資料持續準）；「推薦合作」明確掛在企業帳號之後（Stage 2）。schema 預留 `source` / `public_directory` 即可。

### 11.6 模組職責（付費相關）

```
M1  plan_tier: free | pro | enterprise
    · person_enrich_mode: inference_only | linkedin_llm
    · quotas: search_cache, live_augment, manual_refresh, person_linkedin
    · auto_refresh_*（Pro+）
    · search_precision: strict | balanced | exploratory（§11.9；Free 禁 exploratory）

M3  個人職責推估（Free+）

M3.5  LinkedIn / 公開摘要（Pro+）

M5  搜尋：自己庫 +（Pro+）公開 stub 索引；結果標來源；C1 外链 UX
    · 统一漏斗 intent → hybrid top-K → rerank（DDR-101）
    · search_precision → rerank prompt 严格度（§11.9）；禁止 retrieval fallback 凑数（DDR-99~100）

M6  公司 enrich + manual / stale refresh

M11 公開商務目錄（企業版）：org、Admin、stub、外部 URL、公開/不公開
    · 匯入/HR 串接：企業版 kickoff（DDR-79）

M7  預設私密；私人庫永不進公開索引

UI  Account Hub「我的」（§11.8）：依 tier 組裝區塊；Admin 路由分離
```

### 11.7 決策紀錄（DDR · 2026-06）

| ID | 決策 |
|----|------|
| DDR-74 | 對外只談 **Free｜Pro｜企業版**；不另售第四檔加購方案 |
| DDR-75 | **薄 stub + 外部名片 URL**；不做完整 e-card 宿主 |
| DDR-76 | **Pro = 搜公開目錄（讀）**；**企業版 = 發布 + Admin 管理（寫）** |
| DDR-77 | 企業 **seat 預設全部公開** |
| DDR-78 | **離職/不公開 = Admin 手動下架**（seat 停用不自動移除） |
| DDR-79 | 匯入/HR/SSO **企業版開發時再定**；最小契約：Admin + CSV |
| DDR-80 | Pro 搜到公開身份：**摘要 + 前往外部名片**；不展示電話/Email |
| DDR-96 | **「我的」= 三方案共用 Account Hub**；依 tier 顯示區塊（§11.8） |
| DDR-97 | **搜尋精準度**可持久化；**≠** 業務方向 profile（DDR-5） |
| DDR-98 | Free：**精準+平衡**；**探索**鎖 Pro+（可預覽）；自訂分數 / 組織預設 → 企業 P2 |
| DDR-99 | 禁止低分 fallback 硬塞；`degraded` 不套用探索寬鬆門檻 |
| DDR-100 | 結果卡 **match_sources chips** + degraded 明確 banner |

### 11.8 帳號／我的（Account Hub）分層規劃

> **決策**：三方案共用**同一入口**「我的」，以 `plan_tier` **解鎖區塊**，不做三套獨立帳號頁（DDR-96）。  
> **路由（MVP）**：Web `GET /settings`（現行 SettingsPage 演進）；App 對應底部 Tab「我的」。  
> **與 Admin 分離**：企業公開目錄 **CRUD** 在 `/admin/org`（M11）；「我的」只放**個人偏好 + 組織摘要連結**。

#### 11.8.1 資訊架構（由上而下）

```
我的（Account Hub）
├── 1. 帳號摘要          [Free · Pro · 企業版]
│      顯示名稱、email、方案 badge、（企業版）所屬組織名
├── 2. 本期用量          [Free · Pro · 企業版]
│      搜尋、live 查、手動更新公司、LinkedIn 補充…
├── 3. 搜尋偏好          [Free · Pro · 企業版]  ← §11.9
│      精準度三檔；Free 探索模式鎖定 + CTA
├── 4. 資料更新          [Pro · 企業版]（Free：區塊可見、disabled + CTA）
│      auto refresh、LinkedIn 自動補充（Stage 1 現行）
├── 5. 組織與公開目錄    [僅 企業版]
│      組織名、已發布 stub 數、→「管理公開目錄」(/admin/org)
├── 6. 方案與帳單        [Free · Pro · 企業版]
│      升級 / 試用 Pro、（企業版 P2）seat 與帳單入口
└── 7. 資料與隱私        [Free · Pro · 企業版]
       預設私密說明、刪除帳號、Privacy Strip 詳述連結
```

#### 11.8.2 三方案畫面差異（摘要）

| 區塊 | Free | Pro | 企業版 |
|------|------|-----|--------|
| 1–3、7 | 完整（3 內探索鎖定） | 完整 | 完整 |
| 4 資料更新 | 灰顯 +「升級 Pro」 | 可操作 | 可操作（同 Pro seat） |
| 5 組織 | 隱藏 | 隱藏 | 摘要 + 連 Admin |
| 6 方案 | 升級 CTA | 可改回 Free（dev/Pilot） | 企業合約說明 |

#### 11.8.3 與其他模組邊界

| 模組 | 「我的」內容 | 不在「我的」 |
|------|-------------|-------------|
| **M1** | plan、quota、`search_precision`、auto_refresh 開關 | 計費後台 |
| **M5** | 搜尋精準度偏好（讀寫） | 搜尋執行本身 |
| **M6 / M3.5** | Pro 資料更新開關 | 聯絡人詳情內「更新公司／LinkedIn」 |
| **M11** | 組織摘要、Admin 連結 | stub 列表、CSV、發布下架 |

#### 11.8.4 API / 設定欄位（預留）

`PATCH /api/v1/me/settings` 擴充（與 Stage 1 並存）：

```json
{
  "search_precision": "strict | balanced | exploratory"
}
```

- 預設：`balanced`
- Free 送 `exploratory` → `403 SEARCH_PRECISION_NOT_ALLOWED` 或 silently 降為 `balanced`（ENG 擇一，QA 鎖定）

---

### 11.9 AI 搜尋精準度（分級開放）

> **產品問題**：全鎖設定 → Free 搜不到以為產品壞；全開 → 削弱 Pro 付費誘因。  
> **解法**：**分級開放（teaser + 升級錨點）**（DDR-98）。

#### 11.9.1 三檔精準度（使用者可理解文案）

> **2026-06-17 決策（DDR-101）**：精準度改由 **rerank prompt 语义** 控制 AI 严格程度，**不再**映射服务端 `min_match_score` 过滤。Pilot 数值 0.75 / 0.55 / 0.40 仅作 **LLM 自评 `match_score` 的预期分布参考**（排序与 QA），不作 EMPTY 门槛。

| 模式 | AI 行为（prompt） | 预期体感 | 適用 |
|------|-------------------|----------|------|
| **精準** | 高度确定才推荐；不确定则返回更少或 `[]` | 寧可 EMPTY | 老闆要名單、要確定對口 |
| **平衡**（預設） | 语意相关即可；附 match_reason | 多数日常找商机 | 預設 |
| **探索** | 可列弱相关；仍须 cite 真实字段 | 更多候选、供发散 | 開拓新對象、公開池（Pro+） |

> UI 文案面向使用者，**不**暴露分数门槛。仍**禁止** retrieval 模板 fallback 凑数（DDR-99）。

#### 11.9.1b 两种分数分工（M5 · DDR-101）

| 分数 | 产生阶段 | 用途 | **禁止**用途 |
|------|----------|------|--------------|
| **`retrieval_score`** | Layer A 混合召回（tsvector / pg_trgm / pgvector RRF） | 召回池内排序；多路召回合并去重；工程日志 | 决定 API 是否 EMPTY；替代 LLM 判断相关性 |
| **`match_score`** | Layer B LLM rerank | 最终结果排序；可选 UI 展示；`search_results` 持久化；QA 回归；跨池混排 | 服务端 `if score < 0.55: drop`；与 `search_precision` 硬映射过滤 |

**EMPTY 合法原因**：① 召回+rerank 后 LLM 返回 0 条（含精準 prompt 下 AI 主动不报）；② hard constraint 过滤后 0 条；③ 用户无权搜该池（entitlement）；④ `degraded` 且 fallback 路径无合格候选。**不合法**：因 `match_score` 低于 Pilot 参考值而 silent 丢弃 LLM 已返回的条目。

#### 11.9.2 方案分級開放矩陣

| 能力 | Free | Pro | 企業版 |
|------|:----:|:---:|:------:|
| 精準 | ✅ 可選 | ✅ | ✅ |
| 平衡（預設） | ✅ 可選 | ✅ | ✅ |
| 探索 | 🔒 UI 可見、不可存；文案連結 Pro 價值（跨池 + 放寬匹配） | ✅ | ✅ |
| 自訂滑桿 / 數字門檻 | ❌ | ❌ | 🚧 **Admin 設組織預設**（P2；覆寫 seat 個人預設） |

**Free「探索」鎖定 UX 文案方向**（Pilot 可測）：
> 「Pro：放寬匹配，並搜尋平台公開商務身份」

#### 11.9.3 結果可信度（與 1a / 1b 對齊）

| 規則 | 說明 |
|------|------|
| **禁止 fallback 湊數** | Rerank 無合格結果 → `EMPTY`；不得輸出「文字相關：…」模板分數 0.35 列（DDR-99） |
| **degraded 路徑** | LLM 失敗時標 `degraded=true`；fallback 排序之 `match_score` 仅供参考；UI banner「簡化模式」（DDR-100） |
| **match_sources** | 每張結果卡展示引用欄位 chip（DDR-100） |
| **EMPTY 引導** | 精準模式下 0 結果 → 建議改「平衡／探索（Pro）」或換問法 |

#### 11.9.4 與 DDR-5 的關係

- **允許持久化**：`search_precision`（搜尋 strictness／結果門檻）
- **禁止持久化**：業務方向、產業偏好、固定「我只做 OEM」類 profile
- 每次搜尋仍以**當次自然語言**為意圖來源；精準度只調 **rerank 严格度**，不改寫 query

#### 11.9.5 實施階段

| 階段 | 內容 | 依賴 |
|------|------|------|
| **Stage 1b** | 1a 關 fallback + 1b UI chips/banner + Account Hub 搜尋偏好 + entitlement 分級 | M1 settings API、M5 |
| **Stage 2+** | embedding 混合召回纳入 Layer A（§11.9 三档语意不变；分数分工见 §11.9.1b） | M5 P1 pgvector |
| **Enterprise P2** | Admin 組織預設精準度 | M11 治理 |

---

## 12. M6 公司資訊補全 — PM L3 摘要（v2.1）

> 完整規格：`spec/modules/BSChat_PM_M6.md`

### 12.1 核心能力（P0）

- 收錄後背景 enrich：**主要產品/服務** + 官網 + provenance + `enriched_at`
- 信心門檻：products confidence ≥ **0.5** 才顯示；0.3–0.49 顯示「資訊不足」
- 同一使用者下 Company 去重；多 Contact 共享 enrich 結果
- 觸發 M3 inference pass 2 + 搜尋 re-index（`CompanyEnriched`）

### 12.2 資料新鮮度三層

| 層級 | 時機 | 模組 | 方案 |
|------|------|------|------|
| Layer 1 Cache-at-ingest | 收錄時 | M6 | Free + Pro |
| Layer 2 Stale auto-refresh | enriched_at > N 天 | M6（M1 開關） | **Pro only** |
| Layer 3 Query-time | 搜尋/問 AI 時 | M5 | Free 試用 / Pro 放寬 |

### 12.3 明確不做

- 人員離職/在職追蹤（DDR-33）
- 以名片快照為準；UI 可標「名片資料 · 收錄於 [date]」

### 12.4 User Stories（M6）

- **US-6.1** 主要產品自動補全（收錄時）
- **US-6.2** 接受 / 拒絕 / 覆寫 AI 補全
- **US-6.3** 名片庫列表顯示公司產品摘要
- **US-6.4** 補全完成觸發 M3 職責推估 pass 2
- **US-6.5** Pro：M1 設定自動更新過期公司資料
- **US-6.6** 手動更新公司資訊（Free 限額 / Pro 放寬）

---

## 12.5 M3.5 個人 LinkedIn 補充 — PM L3 摘要（v2.3 新增）

> 完整規格：`spec/modules/BSChat_PM_M35.md` · 架構：`spec/architecture/BSChat_SA-SD_M35.md`

### 12.5.1 定位

- **Free**：僅 M3 LLM 推估（不收外部 people search 成本）
- **Pro / Enterprise**：在 M3 之上，可透過 **LinkedIn 公開資料 + LLM** 取得較準的個人職責摘要
- **非**在職追蹤、**非**全庫 silent 搜 LinkedIn（DDR-75）

### 12.5.2 觸發

| 觸發 | Free | Pro |
|------|------|-----|
| 收錄後 M3 LLM pass 1/2 | ✅ | ✅ |
| 名片/import 含 `linkedin_url` 自動 M3.5 | ❌ | ✅（預設開；可關） |
| 詳情「LinkedIn 補充」按鈕 | ❌（升級 CTA） | ✅ 扣 monthly quota |
| M5 結果「深入查此人」 | ❌ | ✅ 扣 quota |

### 12.5.3 User Stories

- **US-3.5.1** Pro 使用者希望從 LinkedIn 公開資料核對聯絡人負責範圍，以便比 LLM 推估更準地決定是否 follow-up
- **US-3.5.2** Free 使用者仍能看到 M3 AI 推估；點 LinkedIn 功能時看到升級說明，而非錯誤
- **US-3.5.3** 系統在 match 不確定時只顯示候選、不寫入，避免錯人

### 12.5.4 資料來源與呈現決策（DDR · 2026-06-11 · pm-role 拍板）

> 細節與 UI 標籤見 `spec/product/BSChat_M35_data_source.md`。本次拍板使文件與既有實作對齊，解除 M3.5 紅旗 3。

| ID | 決策 |
|----|------|
| DDR-81 | M3.5 `person_scope` 與 M3 `responsibility_scope` **分區呈現**；M3 推估降為「系統參考（名片推估）」置上方 |
| DDR-82 | LinkedIn 路徑失敗採**混合 fallback**：有 URL 讀不到 → 停下問使用者（不自動 fallback）；無 URL 且搜尋 0 筆 → 自動 `card_inference` |
| DDR-83 | 有 URL 但讀不到 → `data_source=unavailable` + `status=insufficient`，提示確認連結 / 自行輸入，**不扣額度** |
| DDR-84 | `card_inference` **免費**（不扣 LinkedIn 月額度、不扣 M3 額度） |
| DDR-85 | `data_source` 正式採 **6 類**：`linkedin_profile` / `linkedin_search` / `linkedin_url_public` / `card_inference` / `user_manual` / `unavailable`（修正 6/3 草案 4 類漂移） |

---

## 13. Phase 3 — 授權公開商務池 + 企業公開目錄（v2.2 新增）

> **方案分層以 §11 v2.4 為準**（Free｜Pro｜企業版）。本章說明 Phase 3 的**資料池與模組分工**；收費與賣點見 §11。

> **決策摘要（2026-05 產品討論）**：  
> 不搜別人的人脈；只搜**自願公開**的商務身份。  
> 與企業合作：企業付訂閱、Admin 發布員工公開商務身份，進入**公開可搜池**；**Pro** 使用者 AI 搜尋可含此池；**Free** 仍限**自己的名片池**。

### 13.1 兩個搜尋池（Search Pools）

```
┌─────────────────────────────────────────────────────────┐
│  Pool A — 私人名片池（Private Rolodex）                  │
│  · 使用者自己掃描/匯入的聯絡人                           │
│  · 預設私密（M7）                                        │
│  · MVP M5：只搜這個池                                    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Pool B — 授權公開商務池（Public Business Directory）    │
│  · 企業 Admin 發布的員工公開商務身份（主路徑）           │
│  · 未來：個人自願發布自己的商務身份（次路徑）            │
│  · 明確 opt-in；可隨時撤回                               │
│  · Phase 3：**Pro / 企業版** 可搜                        │
└─────────────────────────────────────────────────────────┘
```

**同一個對話式搜尋 UI**，但 scope 不同：

| 使用者方案 | 可搜 Pool A（自己庫） | 可搜 Pool B（公開目錄） |
|------------|:---------------------:|:-----------------------:|
| Free | ✅ | ❌ |
| Pro | ✅ | ✅ |
| 企業版 | ✅ | ✅（另可 **發布/管理** 自家目錄） |

結果卡必須標示來源：**「你的名片庫」** vs **「公開商務 · {公司名}」**（見 DDR-80）。

### 13.2 企業合作模式（Supply Side）

**價值主張（對企業）**：
- 統一對外商務窗口、品牌一致
- 員工公開身份可被 BSChat **Pro 用戶**以自然語言找到（精準曝光）
- 不需自建 SEO / 黃頁；AI 匹配「誰做工業電腦 OEM」時出現你們的人

**流程（概念）**：

```
企業簽 企業版 訂閱
    → 建立 Organization + Admin
    → 批量/CSV 建立員工公開商務身份（薄 stub + 外部名片 URL）
    → Admin 發布至公開池
    → 名片進入 public_directory index
    → Pro / 企業版 用戶可搜尋到
```

**企業控管**：
- Admin 可停用離職員工身份（即時下架）
- MVP：**不在 BSChat 展示**公開身份的電話/Email；Pro 只見摘要 + 前往外部名片（DDR-80）
- 用量報表：被搜尋次數、被查看次數（Phase 3 後期）

**模組歸屬（規劃）**：
- **M11 企業公開商務目錄**：Org、Admin、stub CRUD、發布至公開池
- **M5b 跨池搜尋**：私人池 + 公開池检索、结果来源标注
- **M1**：Free / Pro / 企業版 方案与 quota

### 13.3 個人使用者（Demand Side · Pro）

MVP / Free：只搜 Pool A，確保 Aha Moment。

**Pro（Stage 2）**：
- 同一對話：「我手上有誰 / **平台上有誰** 做工業電腦的？」
- 或 UI 切換：「含公開商務池」
- 匹配理由同上（公司產品 + 職責），但标注 **公開池來源**

Free 用戶若嘗試含公開池 → 升級 Pro CTA（可選 teaser：「公開池有 N 条匹配」）。

### 13.4 與 MVP 的邊界（不阻塞 Phase 1）

| 項目 | MVP（Phase 1） | Phase 3 |
|------|----------------|---------|
| M5 搜尋範圍 | 仅 Pool A | + Pool B（Pro+） |
| 公開商務身份 | 無 | M11 Admin 發布 stub |
| Index | `contact_search_documents` | + `public_directory_documents` |
| 隐私 | 全部 private | 公开池独立实体，不泄露 private |
| 收費 | Free + Pro（自己庫 + 資料新鮮度） | + **企業版**（發布目錄） |

**MVP 架构预留（低成本）**：
- M5 API 预留 `search_scope: private | network | all`（默认 private）
- 结果 schema 预留 `source_pool: private_rolodex | public_directory`

### 13.5 信任与合规

| 原则 | 说明 |
|------|------|
| 默认私密 | 扫进来的第三方名片**永远**在 Pool A，不可被他人搜 |
| 自愿公开 | 进 Pool B 须企业 Admin 主动发布（MVP）；完整版可加員工二次確認 |
| 可撤回 | 下架后 24h 内从 index 移除 |
| 透明 | 公开池结果卡显示「公開商務 · 非来自他人私人库」 |
| 不转售人脉 | 禁止「上传通讯录换曝光」类模式 |

### 13.6 Phase 3 User Stories（摘要）

**US-11.1 企業 Admin 發布公開商務身份**
> As a 企業 Admin, I want to 在 BSChat 建立並發布員工公開商務身份, so that 我們的窗口能被 Pro 用戶 AI 搜尋找到。

**US-5.7 搜尋公開商務池（Pro）**
> As a B2B 業務代表（Pro）, I want to 在對話搜尋中包含 BSChat 公開商務池, so that 我不只找自己收過的名片，還能找到新的潛在窗口。

Acceptance Criteria:
- Given Free, When 搜尋含公開池, Then 403 或僅 Pool A + 升級 CTA
- Given Pro, When 搜尋含公開池, Then Pool A + B，结果分組或标注来源
- Given 企业 Admin 下架员工, When 再搜尋, Then 该员工不出现在 Pool B

**US-11.2 員工同意公開**
> As a 企業員工, I want to 確認是否同意我的公開身份被平台用戶搜尋, so that 我掌握曝光範圍。（MVP 簡化：Admin 發布即 org 授權）

### 13.7 新增 DDR

| ID | 決策 |
|----|------|
| DDR-58 | AI 搜尋分 **Pool A（私人）** 与 **Pool B（授权公开）**；MVP 仅 A |
| DDR-59 | **禁止**搜尋他人私人收錄的聯絡人；Pool B 仅自愿公开的商務身份 |
| DDR-60 | 企業公開目錄（M11）为 Pool B **主路径**；企业订阅换可搜曝光 |
| DDR-61 | Free 不開 Pool B；**Pro / 企業版** 可搜 Pool B |
| DDR-62 | 公开池与私人库 **索引隔离**；private contact 永不进入 public index |

### 13.8 冷啟動与 GTM 建议

1. **MVP 先验证 Pool A** — 个人 Aha 成立后再推 Pro 跨池
2. **Enterprise 锚定客户** — 先签 2–3 家愿意公开目录的 B2B 厂商（工业电脑、自动化等垂直）
3. **Pro 升級敘事** — 強調「推薦可合作的名片」；Free 可選 teaser「公开池有 N 条匹配，升级 Pro 查看」（Pilot 定）

---

## Appendix A — 訪談 Q&A 紀錄摘要

| # | 問題 | 回答 |
|---|------|------|
| Q1 | 第一個付費使用者是誰？ | B2B 業務代表（使用者本人） |
| Q2 | 核心痛點？ | 忘記對方公司做什麼；名片會不見；無法判斷關聯度 |
| Q3 | 老闆要名單時要什麼？ | 都有可能；有時從名片找潛在商機 |
| Q4 | 現在怎麼找？ | Google 查公司 → 對照手中名片 |
| Q5 | 卡在哪？ | 全部都有（記不起/看不懂/找不到/不確定） |
| Q6 | 最讓你放棄的？ | B（看不出公司做什麼）+ E（整體都會） |
| Q7 | 夠用的資訊？ | 公司主要產品 + 個人負責業務 |
| Q8 | 個人業務怎麼來？ | B（AI 推估）；A 不可能（名片都會不見） |
| Q9 | AI 推錯能接受嗎？ | B（勉強可以，常錯就不用了） |
| Q10 | 願意掃多少舊名片？ | A（10 分鐘內），前提是操作簡單 |
| Q11 | 「簡單」的定義？ | 連拍 → 延後只確認姓名/公司 |
| Q12 | 電子名片來源？ | A（LINE/Email 連結）+ B（展覽 QR） |
| Q13 | 收到電子名片後？ | A（留聊天記錄不管） |
| Q14 | 理想的收法？ | A（貼連結）or C（掃 QR） |
| Q15 | 找到後做什麼？ | A（複製聯絡）or D（App 內發送） |
| Q16 | 多久需要搜尋一次？ | 不一定（事件驅動） |

---

*文件版本：v2.5 | 更新：2026-06-16 | 新增：§11.8 帳號／我的分層、§11.9 搜尋精準度分級、DDR-96~100、US-1.4 / US-5.3*
