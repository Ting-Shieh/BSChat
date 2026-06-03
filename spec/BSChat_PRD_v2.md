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
| N-08 | 固定業務方向設定過期 | 設定無效 | 搜尋結果偏離 | 對話式即時意圖，不固定儲存 |

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
| DDR-72 | **UI 只顯示 Pool A「可搜尋」人數**；`indexed_count` 限指**自己名片庫已建索引**且**刪除同步遞減**；Pool B / 非自己庫的 AI 推薦來源**不共用「已索引」文案**，Pro/Phase 3 另列「商務網絡」或結果 `source_pool` | 避免「已索引 vs 聯絡人總數」雙數字混淆；為 Network Explorer / 庫外推薦預留語意 | M5、M3、M11、M1 |
| DDR-73 | 對話式搜尋解析**多維度查詢條件**（公司/產業/場合/職能/地區等），**不限於職稱字面**；使用者明確約束（如「架構師就好」）視為**硬條件**，跨欄位比對（`title`、`responsibility_scope`、`company_products`、`company_name`、`source_label` 等），**不符合則不返回**；禁止 `match_reason` 寫「不符合」卻仍出現在結果中 | 使用者用產業/公司/情境問法多樣；召回+rerank 易「部分相關就列出」；硬條件寧可 NO_MATCH（延續 DDR-5） | M5 搜尋、M3、M6 |
| DDR-74 | **個人職責理解分層**：Free = M3 LLM 推估（title + company + M6 products）；Pro/Enterprise = 可加 **M3.5 LinkedIn + LLM** 個人公開資料補充；Free **永不**觸發外部 people search | 持續 API 成本與錯人風險應付費；Free 仍保留 Aha（公司 + 推估）；LinkedIn 資料經第三方/API，非 M6 公司 enrich | M3、M3.5、M1 |
| DDR-75 | M3.5 **不自動對全庫 silent 搜人**；僅：① 名片/import 含 `linkedin_url` 且 Pro ② 使用者手動「LinkedIn 補充」③ Enterprise 可配置 batch（Phase 2）；`match_score < 0.8` 不寫入 Contact | 同名消歧與合規；寧可提示確認也不錯人寫庫 | M3.5、M1 |
| DDR-76 | M3.5 成功結果 **不覆寫** OCR `title`；寫入 `person_responsibility_scope`（或增強 `responsibility_scope`）並標 `provenance=linkedin`；M5 硬匹配需 `person_match_score ≥ 0.8` 且 confidence ≥ 0.75 | 名片為交換快照；LinkedIn 為補充視角 | M3.5、M5、M3 |

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

## 11. 商業模式與付費分層（v2.1 新增）

### 11.1 定價原則

> **免費層解決「當時看懂」；付費層解決「長期保持準確」。**

- 不鎖定 **第一次 enrich** 或 **基本搜尋（cache）** —— 避免打掉 Aha Moment
- 持續 API 成本的功能（自動刷新、live 查、高頻手動更新）→ 付費合理

### 11.2 方案對照（摘要）

> **完整對照表**：§11.2.1（Personal Free / Pro）· §11.2.2（Enterprise Personal · Phase 2）· §11.2.3（Enterprise Publisher · Phase 3）  
> **Quota 數字**：均為 **Pilot 測試暫定值（TBD）**，上線前鎖定；MVP 實作可先 hardcode，schema 預留。

| 能力 | Free | Pro |
|------|------|-----|
| 收錄 + 公司 enrich + M3 LLM 推估 + Pool A 搜尋 | ✅ | ✅ |
| M3.5 LinkedIn + LLM 個人補充 | ❌ | ✅ |
| 手動「更新公司資訊」（M6） | 有限額 | 較高額度 |
| 過期自動 refresh 公司資料 | ❌ | ✅ |
| Pool B 公開商務池 | ❌ | ❌（見 §11.2.3 / §13） |

*Pro 價格 Pilot 後驗證（例如 NT$299/月），不作為 MVP 阻塞項。*

---

### 11.2.1 Personal 方案總對照（Free · Pro）

**適用對象**：個人業務；只搜尋**自己收錄**的名片池（Pool A）。  
**MVP 範圍**：先實作 **Free + Pro**；Enterprise 見 §11.2.2 / §11.2.3。

#### 名詞：「手動更新公司資訊」是什麼？（M6 · 非 LinkedIn）

指使用者在聯絡人詳情 **「公司補全」區** 點 **「更新公司資訊」**，系統**重新抓取公司官網 + LLM**，更新 **主要產品/服務**（`main_products`）。

| 機制 | 觸發 | 更新對象 |
|------|------|----------|
| 收錄時 enrich（Layer 1） | 收名片後自動 | 公司產品 |
| **手動更新公司（M6 manual refresh）** | **使用者按鈕** | 公司產品 |
| 過期自動 refresh（Layer 2，Pro） | 背景排程 | 公司產品 |
| M3.5 LinkedIn 補充（Pro） | 按鈕 / URL 自動 | **個人**職責（另一套 quota） |

#### A. 收錄與名片庫（M2 / M3 / M7）

| 能力 | Free | Pro |
|------|:----:|:---:|
| 批次連拍 / QR / 貼連結收錄 | ✅ | ✅ |
| 背景 OCR + 待確認 | ✅ | ✅ |
| 名片庫列表 / 詳情 | ✅ | ✅ |
| 名片原文（OCR）+ Provenance | ✅ | ✅ |
| 軟刪除 / 預設私密（Pool A） | ✅ | ✅ |
| 儲存 `linkedin_url`（不抓取） | ✅ | ✅ |

#### B. 公司理解（M6）

| 能力 | Free | Pro |
|------|:----:|:---:|
| 收錄時公司 enrich 一次 | ✅ | ✅ |
| 詳情 / 列表看主要產品 | ✅ | ✅ |
| 接受 / 拒絕 / 覆寫公司 AI 補全 | ✅ | ✅ |
| **手動「更新公司資訊」**（M6 manual refresh） | ✅ **3 次/月** ※ | ✅ **50 次/月** ※ |
| 過期自動 refresh（>N 天背景更新） | ❌ | ✅（預設 90 天，可調 30/60/90） |
| enrich 優先佇列 | ❌ | ✅ P2 |
| 人員在職 / 離職追蹤 | ❌ | ❌ |

※ **TBD**：Pilot 測試後調整；Pro「50 次/月」為暫定，可能改為更高或「近無限」。

#### C. 個人職責（M3 + M3.5）

| 能力 | Free | Pro |
|------|:----:|:---:|
| **M3 LLM 推估**（title + company + M6 products） | ✅ | ✅ |
| confidence < 0.6 不顯示 | ✅ | ✅ |
| **M3.5 LinkedIn + LLM 個人補充** | ❌ | ✅ |
| 名片含 LinkedIn URL → 自動 M3.5 | ❌ | ✅（預設開，可關） |
| 詳情「LinkedIn 補充」手動 | ❌ | ✅ |
| M5「深入查此人」→ M3.5 | ❌ | ✅ P1 |
| **person_linkedin 月度額度** | **0** ※ | **20 次/月** ※ |
| URL 自動 M3.5 是否占 manual quota | — | **不占** ※ |

※ **TBD**：Pilot 後鎖定。詳規：`spec/modules/BSChat_PM_M35.md`

**Free UX**：詳情顯示 M3「AI 推估」+ Pro 升級 CTA；不呼叫 M3.5 API。

#### D. AI 搜尋（M5 · 僅 Pool A）

| 能力 | Free | Pro |
|------|:----:|:---:|
| 對話式搜尋（已索引 cache） | ✅ | ✅ |
| **search_cache 每日額度** | **10 次/日** ※ | **50 次/日** ※ |
| 個人化搜尋建議 chips | ❌ | ✅ P1 |
| M5 **live 上網查**（公司，Layer 3） | **5 次/月** ※ | **30 次/月** ※ |
| 搜尋 Pool B 公開商務池 | ❌ | ❌ |

※ **TBD**：Pilot 測試暫定值。

#### E. 行動與其他（M8 / M4 / M1）

| 能力 | Free | Pro |
|------|:----:|:---:|
| 複製電話 / Email（M8） | ✅ | ✅ |
| 重複偵測 Email/電話（M4） | ✅ P1 | ✅ P1 |
| 升級 / 帳單 / 用量顯示 | — | ✅ |

#### F. 一句對照（行銷用）

| | Free | Pro |
|---|------|-----|
| **賣點** | 收錄即看懂公司 + LLM 推估 + 找得到人 | 資料更新 + LinkedIn 核對職責 + 較高搜尋/live 額度 |
| **不賣** | LinkedIn 個人補充、auto refresh、高頻 live 查 | Pool B 公開池（Phase 3） |

---

### 11.2.2 Enterprise Personal（團隊採購 · Phase 2 · 邊做邊定）

> **與 §11.2.1 的 Pro 同屬 Pool A 私人名片庫**；不是公開目錄。MVP **可不實作**，schema / 文案預留。

**誰買**：公司為 **自己的業務團隊** 採購（多 seat）。

**做什麼**：
- 每位成員 **各自收名片**、**只搜自己庫**（與 Free/Pro 相同產品邏輯）
- 比 Pro 更高 quota、團隊帳單、管理與稽核（Phase 2）

**不做什麼**：
- ❌ 不公開成員收錄的私人聯絡人給其他 BSChat 用戶
- ❌ 不是 HR / 在職追蹤（DDR-33）

| 能力（相對 Pro） | Enterprise Personal ※ |
|------------------|----------------------|
| 包含 Pro 全部能力 | ✅ |
| person_linkedin / 月 | **100** ※（或合約） |
| search_cache / 日 | **100** ※ |
| live 查 / 月 | **100** ※ |
| 手動更新公司 / 月 | **100** ※ |
| 團隊共享 person quota | Phase 2 |
| 操作 audit log | Phase 2 |
| 全庫 batch person enrich | Phase 2（admin opt-in） |
| People API SLA | 合約 |

※ **TBD** · 詳見 `spec/modules/BSChat_PM_M35.md` F-35.11 / F-35.12

**類比**：公司團購「加強版 Pro」—— 仍是私人抽屉，不是公司對外黃頁。

---

### 11.2.3 Enterprise Publisher（企業公開目錄 · Phase 3 · 邊做邊定）

> **與 §11.2.2 完全不同產品線**；完整願景見 **§13**。MVP **不實作**。

**誰買**：B2B 企業（例如設備商、SI 廠商）。

**做什麼**：
- 企業在平台 **建立 / 維護員工電子名片**（自願公開）
- **其他** 付費用戶可透過 **Pool B / Network Explorer** 搜到這些人

**不做什麼**：
- ❌ 不公開「業務員抽屉裡收來的私人名片」
- ❌ Personal Free/Pro 用戶 **不能** 因此搜到他人私人庫

| 能力 | Free | Pro | Enterprise Publisher |
|------|:----:|:---:|:--------------------:|
| 搜尋自己的 Pool A | ✅ | ✅ | ✅（企業 admin 亦可用） |
| 建立 / 維護 **公開** 員工電子名片 | ❌ | ❌ | ✅ |
| 被 Network Explorer 搜到（Pool B） | ❌ | ❌ | ✅ |
| 搜尋他人 **私人** 收錄聯絡人 | ❌ | ❌ | ❌ |

**類比**：企業維護 **官方可被找到的人員目錄**（供給端）；Personal 用戶是 **需求端** 搜自己庫或未來搜公開池。

**雙邊收費**（§11.5）：需求端 Network Explorer；供給端 Enterprise Publisher 年訂閱。

---

### 11.3 模組職責（付費相關）

```
M1 帳號/訂閱（設定入口）
  · plan_tier: free | pro | enterprise
  · auto_refresh_enabled（Pro）
  · auto_refresh_interval_days
  · manual_refresh 月度配額與用量
  · person_enrich_mode: inference_only | linkedin_llm（DDR-74）
  · person_linkedin_quota_monthly / used / reset_at
  · person_linkedin_auto_on_url（Pro 開關）
  · 升級/帳單 UI

M3 個人職責推估（Free + Pro 共用）
  · Pass 1/2 LLM inference；confidence gate 0.6
  · 寫入 contacts.responsibility_scope

M3.5 個人公開資料補充（Pro；Enterprise Personal 見 §11.2.2）
  · People search API 或 LinkedIn URL extract + LLM 摘要
  · match_score gate 0.8；讀 M1 entitlement；Free 入口 hard block
  · 詳見 spec/modules/BSChat_PM_M35.md · 方案對照 PRD §11.2.1

M6 公司補全（執行引擎）
  · ingest / manual / stale_auto enrich（僅公司；不做個人 LinkedIn）
  · 讀取 M1 entitlement 決定是否跑 stale job
  · enriched_at、provenance

M5 AI 搜尋
  · query-time live 查（受 plan 額度限制）
  · 合併 cache + live 結果；不自動覆寫 cache（DDR-36）
  · 詳情/M5 可觸發 M3.5「深入查此人」（扣 person_linkedin quota）
```

### 11.4 Team 版（Phase 2 · 對齊 §11.2.2 Enterprise Personal）

- 共享 refresh 策略、團隊用量報表、集中 enrich / person_linkedin 配額
- **非** Enterprise Publisher（§11.2.3）；仍只操作 Pool A 私人庫

### 11.5 Enterprise + 公開商務池（Phase 3 · v2.2）

> 完整對照 **§11.2.3 Enterprise Publisher**。MVP **不**實作跨池搜尋；Personal Pro 仍只搜自己的名片池。

| 方案 | 對象 | 核心能力 | 定價方向 |
|------|------|----------|----------|
| **Personal Free / Pro** | 個人業務 | 搜尋**自己的**名片池 + 資料新鮮度 | 見 **§11.2.1** |
| **Enterprise Personal** | 團隊採購 | Pro + 更高 quota / 稽核（Pool A） | 見 **§11.2.2** |
| **Network Explorer** | 個人（加購或高階） | 額外搜尋**授權公開商務池** | Pilot 後定 |
| **Enterprise Publisher** | B2B 企業 | 建立公開員工電子名片 → 可被搜尋 | 見 **§11.2.3** · §13 |

**雙邊收費邏輯**：
- **需求端**：付費才能搜公開池（不動 MVP 免費搜自己庫的 Aha）
- **供給端**：企業付費建立/維護電子名片目錄，換取曝光與被找到

**紅線（不可妥協）**：
- ❌ 不搜尋他人「收進來的私人聯絡人」
- ✅ 只搜**自願公開**的商務身份（企業員工電子名片、未來可含個人自發布）

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

---

## 13. Phase 3 — 授權公開商務池 + 企業電子名片（v2.2 新增）

> **決策摘要（2026-05 產品討論）**：  
> 不搜別人的人脈；只搜**自願公開**的商務身份。  
> 與企業合作：企業付訂閱、在平台建立員工電子名片，員工名片進入**公開可搜池**；一般使用者 AI 搜尋預設仍限**自己的名片池**。

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
│  · 企業在 BSChat 建立的員工電子名片（主路徑）            │
│  · 未來：個人自願發布自己的商務身份（次路徑）            │
│  · 明確 opt-in；可隨時撤回                               │
│  · Phase 3 M5b：Network 訂閱者可搜                       │
└─────────────────────────────────────────────────────────┘
```

**同一個對話式搜尋 UI**，但 scope 不同：

| 使用者方案 | 可搜 Pool A | 可搜 Pool B |
|------------|:-----------:|:-----------:|
| Free / Personal Pro | ✅ | ❌ |
| Network Explorer | ✅ | ✅ |
| Enterprise Publisher 員工 | ✅ | ✅（自家目錄管理） |

結果卡必須標示來源：**「你的名片庫」** vs **「BSChat 公開商務池 · {公司名}」**。

### 13.2 企業合作模式（Supply Side）

**價值主張（對企業）**：
- 統一員工電子名片、品牌一致
- 員工名片可被 BSChat 用戶以自然語言找到（精準曝光）
- 不需自建 SEO / 黃頁；AI 匹配「誰做工業電腦 OEM」時出現你們的人

**流程（概念）**：

```
企業簽 Enterprise 訂閱
    → 建立 Organization + 品牌模板
    → 批量/邀請建立員工電子名片
    → 員工確認「同意公開至 BSChat 商務池」
    → 名片進入 public_directory index
    → Network Explorer 用戶可搜尋到
```

**企業控管**：
- Admin 可停用離職員工名片（即時下架）
- 可設定哪些字段公開（電話/Email 可選隱藏或「請求聯絡」）
- 用量報表：被搜尋次數、被查看次數（Phase 3 後期）

**模組歸屬（規劃）**：
- **M11 企業電子名片**：建立、模板、Org 管理、發布至公開池
- **M5b Network Search**：跨池检索、结果来源标注
- **M1**：Enterprise / Network 方案与 quota

### 13.3 個人使用者（Demand Side）

MVP 不變：Free/Pro 只搜 Pool A，確保 Aha Moment。

Phase 3 加購 **Network Explorer**：
- 同一對話：「我手上有誰 / **平台上有誰** 做工業電腦的？」
- 或 UI 切換：「含公開商務池」
- 匹配理由同上（公司產品 + 職責），但标注 **公開池來源**

### 13.4 與 MVP 的邊界（不阻塞 Phase 1）

| 項目 | MVP（Phase 1） | Phase 3 |
|------|----------------|---------|
| M5 搜尋範圍 | 仅 Pool A | + Pool B |
| 電子名片 | M2 匯入**他人**連結/QR | M11 **建立自己**的電子名片 |
| Index | `contact_search_documents` | + `public_directory_documents` |
| 隐私 | 全部 private | 公开池独立实体，不泄露 private |
| 收費 | Personal Pro = 資料新鮮度 | + Enterprise + Network Explorer |

**MVP 架构预留（低成本）**：
- M5 API 预留 `search_scope: private | network | all`（默认 private）
- 结果 schema 预留 `source_pool: private_rolodex | public_directory`

### 13.5 信任与合规

| 原则 | 说明 |
|------|------|
| 默认私密 | 扫进来的第三方名片**永远**在 Pool A，不可被他人搜 |
| 自愿公开 | 进 Pool B 必须本人 +（企业场景）Admin 双重确认 |
| 可撤回 | 下架后 24h 内从 index 移除 |
| 透明 | 公开池结果卡显示「公开商務身份 · 非来自他人私人库」 |
| 不转售人脉 | 禁止「上传通讯录换曝光」类模式 |

### 13.6 Phase 3 User Stories（摘要）

**US-11.1 企業建立員工電子名片**
> As a 企業 Admin, I want to 在 BSChat 批量建立品牌一致的員工電子名片, so that 我們的窗口能被 AI 搜尋找到。

**US-5.7 搜尋公開商務池（Network Explorer）**
> As a B2B 業務代表, I want to 在對話搜尋中包含 BSChat 公開商務池, so that 我不只找自己收過的名片，還能找到新的潛在窗口。

Acceptance Criteria:
- Given Personal Pro 无 Network, When 搜尋, Then 仅 Pool A
- Given Network Explorer, When 搜尋, Then Pool A + B，结果分組或标注来源
- Given 企业下架员工, When 再搜尋, Then 该员工不出现在 Pool B

**US-11.2 員工同意公開**
> As a 企業員工, I want to 確認是否同意我的電子名片被平台用戶搜尋, so that 我掌握曝光範圍。

### 13.7 新增 DDR

| ID | 決策 |
|----|------|
| DDR-58 | AI 搜尋分 **Pool A（私人）** 与 **Pool B（授权公开）**；MVP 仅 A |
| DDR-59 | **禁止**搜尋他人私人收錄的聯絡人；Pool B 仅自愿公开的商務身份 |
| DDR-60 | 企業電子名片（M11）为 Pool B **主路径**；企业订阅换可搜曝光 |
| DDR-61 | Personal Free/Pro 不锁 Pool A；Network Explorer 才开放 Pool B |
| DDR-62 | 公开池与私人库 **索引隔离**；private contact 永不进入 public index |

### 13.8 冷啟動与 GTM 建议

1. **MVP 先验证 Pool A** — 个人 Aha 成立后再推 Network
2. **Enterprise 锚定客户** — 先签 2–3 家愿意公开目录的 B2B 厂商（工业电脑、自动化等垂直）
3. **Network Explorer 定价** — 按查询次数或月费；免费用户可见「公开池有 N 条匹配，升级查看」teaser（可选，Pilot 定）

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

*文件版本：v2.3 | 更新：2026-05-20 | 新增：§11.2.1~11.2.3 方案总对照、M3.5 付費切割、Enterprise Personal / Publisher 分节*
