# Kickoff: 企業租戶完整 B（M1＋M11）· 2026-07-16

## 1. 模組目的（一句話複習）
落地 **企業租戶完整模型 B**：申請／核准、唯一主 Admin、企業席次邀請控名單、轉移／移除、B1 進租戶＝enterprise；並讓**本公司業務**可被 Admin 邀請進來測試。  
對應：PRD v4 §6.6、DDR-v4-9、`BSChat_enterprise_tenant_model_B.md`、US-v4-4／4b／4c。

## 2. 在系統架構裡的位置
- 我依賴誰：M1 密碼進場（已完成）、既有 Org／OrgMember／invite、M11 電子名片 opt-in
- 誰依賴我：M11 Admin 治理、M5b 公開供給品質、業務 dogfood
- 對外介面：企業申請 API、核准／開通（營運）、企業邀請 CRUD、成員列表／移除、Admin 轉移；前端 `/enterprise/apply`、企業 join、Admin 後台擴充

## 3. 存在性審視（強制三問）
- [x] 還該存在嗎？→ **是**（無控名單則公開供給不可信；業務測也需要）
- [x] 範圍還對嗎？→ **完整 B**（用戶明確要求）；暫緩次 Admin／SSO／正式金流
- [x] 依賴還對嗎？→ **是**；進場與 M11 已有，本切片補「租戶治理」

> **判斷**：合理且急迫。舊「人工改 plan_tier」不足以給業務測；必須產品化 Admin 邀請流。

## 4. 自上次工作以來，上游有變動嗎？
- PRD：新增 §6.6、DDR-v4-9；企業路徑覆寫
- 產品定義：`BSChat_enterprise_tenant_model_B.md` 已鎖定
- 鄰近：M1 進場 Code ✅；M11 opt-in ✅；一般 invite 仍在，需與企業邀請區隔
- 本切片＝**完整 kickoff**（新能力包）

## 5. 本次 session 範圍
- 階段：**SA/SD → UIUX → ENG**（Code 下一輪）
- 產出：[`SA-SD`](../architecture/BSChat_SA-SD_enterprise_tenant_B.md)、[`UIUX`](../design/BSChat_UIUX_enterprise_tenant_B.md)、[`ENG`](../engineering/BSChat_ENG_enterprise_tenant_B.md)
- 完成標準：可回答「如何開本公司給業務測、邀請與舊 join 如何分開、移除成員後方案與公開名片怎麼辦」→ ✅

## 6. 🚩 紅旗
- **無阻塞開工 Code**
- Dogfood 實開時再收：公司顯示名／slug／主 Admin Email
- 舊「任何人 create team」與「企業租戶」並存時，文案必須清楚，避免以為建團隊＝企業

## 7. 決議
- [x] 通過，開工 SA/SD（用戶 2026-07-16「通過」）
- [x] SA／UI／ENG 完成（2026-07-16）→ Code
- [x] Code 完成（2026-07-16）— dogfood：註冊 Admin → `scripts.provision_enterprise` → 邀業務
- [ ] 暫停，回上游：________
