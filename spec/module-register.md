# Module Register / 模組註冊表 — BSChat

最後更新：2026-07-16（企業完整 B：Code ✅ · migration 022）

> 📄 **PRD**：`spec/BSChat_PRD_v4.md`（已確認；§6.6 企業 B）。  
> 企業模型：`spec/product/BSChat_enterprise_tenant_model_B.md`（完整實作＋業務 dogfood）。

## 系統一句話定位

AI 商務配對：私有／團隊庫 + 可選公開電子身份；需求當下 Plan 搜尋 → 分區結果與商機簡報。

## 模組清單

| # | 模組 | 一句話目的 | 對應 PRD | 當前階段 | 最近 kickoff / delta check | 紅旗 / 阻塞 |
|---|------|----------|---------|--------|--------------------------|------------|
| M1 | 帳號／進場／方案 | 密碼進場＋**企業租戶 B** | v4 §6.5–6.6 | **企業 B Code ✅**（migration 022） | kickoff ✅；SA/UI/ENG ✅；delta-check 邀請 Email 2026-07-16 ✅ | 與 M11 共切 |
| M11 | 電子名片／企業供給 | 電子名片＋AI 推薦；**primary admin 閘** | v4 §6.6 | opt-in ✅；publish 僅主 Admin | 同上 | – |
| M2 | 名片收錄 | 批次連拍 + OCR + URL/QR/vCard + 延後確認 | v4 Now | 已完成 - 待驗證 | – | – |
| M3 | 聯絡人 + 職責推估 | 結構化聯絡人 + LLM 職責推估 | v4 §2.4 | 已完成 - 待驗證 | – | – |
| M3.5 | 個人 LinkedIn 補充 | Pro：公開資料 + LLM 職責摘要 | v4 Later API | **Pro 就緒** | 2026-06-11 | LinkedIn 官方 API 擱置 |
| M5 | AI 搜尋 | 對話搜尋 + 簡報 + Plan UI + 分區 | v4 §2.1 §5 | **Plan + M1 閘已接** | m5-plan-ui-20260714 ✅ | – |
| M5b | 跨池搜尋 | 庫 + 公開推薦（M1 門檻） | v4 §2.2 | **v4 對齊完成** | [m5b-v4-align](kickoffs/m5b-v4-align-20260714.md) ✅ | – |
| M6 | 公司補全 | enrich + 手動更新 + Pro stale refresh | v4 §2.4 | 已實作 | – | – |
| M7 | 隱私 | 私有過濾 + 公開 opt-in 紅線 | v4 §3 | 已隨各模組 | – | – |
| M8 | 匯出與行動 | 一鍵複製電話 / Email | v4 P1 | 已實作 | – | – |
| M4 | 重複偵測 | Email / 電話比對提示 | – | 未實作 | – | – |

## 模組依賴圖

```
[M1 帳號/訂閱] ──(entitlement + 試用計數)──► [M5 公開步]、[M3.5]、[M6 Pro]
       │
[M2 收錄] ──► [M3 聯絡人/推估] ──► [M5 Plan 搜尋]
       │              │
       └──► [M6 公司補全]
[M11 電子名片 opt-in] ──► [M5b 跨池] ──► [M5 結果分區 B]
[M7 隱私] 橫切 · [M8 行動] 接結果
```

## 維護原則

- PRD v4 確認後，受影響模組細節動工前跑**完整 module-kickoff**
- 每階段完成 → 更新本表；發現紅旗 → 標阻塞並寫原因
