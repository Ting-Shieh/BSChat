# Kickoff: M1 帳號／訂閱（Free 公開推薦終身試用）· 2026-07-14

## 1. 模組目的（一句話複習）
帳號身份 + 方案 entitlement；本次補齊 PRD v4 **Free 搜尋公開推薦終身 2 次、不月重置**，供 M5 Plan 步驟 3／M5b 誠實閘門。  
對應：PRD v4 §4、§6 Next P0、US-v4-5、DDR-v4-3。

## 2. 在系統架構裡的位置
- 我依賴誰（上游）：Auth（JWT／OAuth／magic-link 已落地）；計費仍可 MVP 假切換
- 誰依賴我（下游）：**M5 Plan 步驟 3**、**M5b 跨池消費閘**、M3.5／M6 Pro 額度（既有）
- 對外介面：`GET /me` quotas、`user_entitlements`、搜尋前 `can_consume_public_recommend`（待 SA/SD 定名）

## 3. 存在性審視（強制三問 — 不能略過）
- [x] 這個模組現在還該存在嗎？→ **是**（方案與額度唯一真相來源；不可散落在 M5）
- [x] 範圍還對嗎？→ **本次只做「公開推薦終身試用計數」切片**；不重做整包訂閱／收款；電子名片供給屬 M11
- [x] 依賴關係還對嗎？→ **是**；M1 先於 M5 誠實略過／扣次；M11 供給可並行稍後，但計數 API 契約需先定

> 判斷：M1 仍合理。v4 把「公開池消費」從「Pro 全開／Free 全關」改成「Free 終身 2 次」——屬 entitlement 擴充，不是新模組。範圍收斂避免一次做完整 billing。

## 4. 自上次工作以來，上游有變動嗎？
- PRD：v2.5／v3 → **v4 已確認**（§4 方案門檻、終身 2 次、不月重置）
- 系統架構：無 v4 系統層 SA 重跑；沿用 Modular Monolith + `user_entitlements`（**已知缺口，本 kickoff 後進模組 SA/SD 補契約**）
- project-context：網絡方向、wedge 四題、Plan UI 已落地；試用計數標待 M1
- 鄰近模組：M5 Plan UI 前端以「非 Pro = 略過步驟 3」近似；M11／M5b 仍舊 stub 語意、待各自 re-kickoff

## 5. 本次 session 範圍
- 階段：**SA/SD 細節**（通過後才 UI/UX → ENG → Code → QA；**不跳階段**）
- 預計產出：
  1. `spec/architecture/BSChat_SA-SD_M1.md`（或等價路徑）：終身試用欄位、扣次時機、`/me` 暴露、與 M5 閘門契約
  2. 更新 register／project-context
- 完成標準：SA/SD 可回答「何時扣 1 次、用完後行為、Pro／企業是否永不扣、降級是否保留已用次數」；無實作 code（本階段）

## 6. 🚩 紅旗
- **無阻塞開工 SA/SD**。
- 已知：尚無 M1 專屬 SA/SD 文件；公開池若仍空，試用體感偏弱——屬 M11 供給問題，不阻塞本模組契約設計。
- 提醒：扣次應在「實際查公開池」而非「僅開 Plan UI」，需在 SA/SD 寫死（對齊 PRD「真步驟」）。

## 7. 決議
- [x] 通過，開工 SA/SD（用戶 2026-07-14「通過」）
- [ ] 暫停，回上游：________
