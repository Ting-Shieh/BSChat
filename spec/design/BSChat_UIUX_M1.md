# BSChat UI/UX — M1 公開推薦終身試用（切片）

> **版本**：v1.0  
> **日期**：2026-07-14  
> **依據**：`BSChat_SA-SD_M1.md` v1.0、PRD v4 §4／§5／US-v4-5、`BSChat_Design_Foundation.md`、既有 `SettingsPage`／`SearchPlanPanel`  
> **UI 庫**：沿用 shadcn/ui + Design Foundation tokens（不新選庫）  
> **範圍**：試用剩餘可見、Plan 步驟 3 略過文案、用盡升級 CTA；不重做整包 Account Hub

---

## Delta check（M1 · UI/UX）

已檢查 PRD v4 §4／§5（無新變動）、SA-SD_M1（剛鎖定 DDR-M1-01／02＝A）、register（無新紅旗）、鄰近 M5 Plan UI kickoff（前端近似仍待本切片替換 isPro）  
→ ✅ 開工 UI/UX

---

## 1. 使用者流程

### Happy path（Free · 尚有試用）
1. 開「我的」→ 看到「公開推薦試用 · 剩 N／2（終身）」  
2. 搜尋 → Plan 步驟 3 **active→done**（非略過）  
3. 結果可出現「AI 推薦 · 公開身份」區  
4. 搜尋後「我的」剩餘 −1  

### 池空（DDR-M1-02）
1. 有試用剩餘但 `public_pool_count=0`  
2. Plan 步驟 3 = **skipped**，detail：「目前沒有可推薦的公開身份」  
3. 剩餘**不變**  

### 試用用盡
1. Plan 步驟 3 = **skipped**，detail：「公開推薦試用已用完（終身 2 次）」  
2. 結果區可不顯示 B 區；或顯示虛線空態 + 「升級 Pro 解鎖」  
3. 「我的」試用列：剩 0／2 + 升級 CTA  

### Pro／Enterprise
1. 「我的」顯示「公開推薦 · 方案內無限」  
2. Plan 步驟 3 正常執行（池空仍 skipped）  

---

## 2. 畫面與改動點（無新頁）

| 畫面 | 改動 | PRD |
|------|------|-----|
| **我的** `SettingsPage` | 用量區新增一列公開推薦試用 | §4、US-v4-5 |
| **AI 搜尋** `SearchPage` + `SearchPlanPanel` | `includePublicPool` 改依 entitlement，非單純 isPro；略過文案三種 | §5 |
| **搜尋狀態列** | 可附「公開試用剩 N」或「公開無限」（短） | §4 |

不新增獨立「試用說明」全頁；升級引導用既有切方案（MVP `POST /me/plan`）或連結設定。

---

## 3. 元件 Spec（對應既有）

### 3.1 `MiniQuota`／用量列 — 公開推薦

**Base**：既有 `MiniQuota` 或 `QuotaBar` 變體  
**Free**：

- Label：`公開推薦試用`  
- Value：`剩 {remaining}／2`  
- Hint（一行）：`終身額度 · 不按月重置`  
- `remaining===0`：文字改 `已用完` + 按鈕「升級 Pro」（呼叫既有 `switchPlan('pro')` 或 scroll 到方案區）

**Pro／Ent**：

- Label：`公開推薦`  
- Value：`無限`（或 `方案內`）  
- 不顯示分數進度

**Tokens**：`--color-text-tertiary`、`--color-border`、`--color-primary`（CTA）

### 3.2 `SearchPlanPanel` 步驟 3 detail 文案

| 狀態 | detail |
|------|--------|
| done（有查） | `查詢公開可推薦身份` |
| skipped · 無權限／試用盡 | `略過 · 公開推薦試用已用完（終身 2 次）` |
| skipped · 池空 | `略過 · 目前沒有可推薦的公開身份` |
| skipped · 未含公開（client 選 private） | `略過 · 本次只搜名片庫`（可選；MVP 可與試用盡合併） |

### 3.3 搜尋結果 B 區空態（試用盡）

**Base**：既有 dashed border 空態  
**Copy**：`公開推薦試用已用完。升級 Pro 可繼續從公開身份找商機。`  
**CTA**：`升級 Pro` → 設定頁或 inline switchPlan  

池空（有權限）：維持現有「目前沒有可推薦的公開身份」— **不**推升級。

### 3.4 升級 CTA（MVP）

沿用設定頁方案切換；不新開付款流。  
按鈕：`Button` primary compact。

---

## 4. Tokens

不新增色票；沿用 Foundation。  
可選：無新 CSS 變數。

---

## 5. 互動筆記

| 狀態 | 行為 |
|------|------|
| Loading `/me` | 用量列 skeleton 或隱藏試用列直至就緒 |
| 搜尋中 | Plan 動畫依 `includePublicPool`（搜尋前由 status／me 決定） |
| 403 `PUBLIC_RECOMMEND_TRIAL_EXHAUSTED` | Toast／inline：「試用已用完」；強制改以庫內結果呈現（若 API 降級為 private） |
| A11y | CTA 可鍵盤操作；略過步驟不要只靠顏色（已有「–」圖示） |

**動畫**：不新增；沿用 Plan 步驟 opacity。

---

## 6. 完成標準

- [x] Flow／文案／元件對應既有頁  
- [x] 對齊 SA-SD 扣次與池空規則  
→ 接 ENG  
