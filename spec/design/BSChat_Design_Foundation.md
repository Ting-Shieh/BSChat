# BSChat 平台設計基礎 / Design Foundation

> **版本**：v1.0  
> **適用**：BSChat 全平台（Web PWA 優先，桌面適配）  
> **依據**：`BSChat_PRD_v2.md`、M2 SA/SD Handoff、Primary Persona（B2B 業務代表）  
> **定位**：商務關係智慧平台 — 不是 CRM、不是電子名片產生器

---

## 1. 設計方向

### 1.1 一句話

> **「在需要的時候，立刻找到對的人 —— 專業、透明、不添亂。」**

### 1.2 美學方向：**Refined Utilitarian（精緻實用）**

| 維度 | 選擇 | 理由 |
|------|------|------|
| 調性 | 專業可信 + 行動導向 | B2B 業務場景；老闆要名單、展覽連拍 |
| 密度 | 行動端中等密度；桌面略疏 | 展覽單手操作 vs 桌面搜尋編輯 |
| 視覺重量 | 內容優先，裝飾克制 | 使用者要「看懂公司、找到商機」，不是賞圖 |
| 差異化 | **AI 資訊視覺分層** + **一鍵收錄** | 與一般通訊錄 App 拉開差距 |

### 1.3 設計原則（平台級）

1. **Aha Moment First** — 新用戶 10 分鐘內必須體驗「搜尋有結果」
2. **零摩擦收錄** — 收名片像拍照，不像填表
3. **AI 透明** — 所有 AI 補全/推估必須視覺區隔 + 來源/信心標示
4. **隱私可見** — 「預設私密」常駐可見，不埋在設定深處
5. **原諒式設計** — 跳過、稍後、force 上傳；不懲罰「沒整理」的習慣
6. **行動優先** — 展覽連拍、戶外可讀性優先

---

## 2. 資訊架構（IA）

### 2.1 主導航（Mobile Bottom Tab）

```
┌────────────────────────────────────────────┐
│  🔍 搜尋   │  📇 名片庫  │  ➕ 收錄  │  ✓ 待確認  │  👤 我的  │
└────────────────────────────────────────────┘
         ↑ 預設 Tab 依情境切換（見 2.2）
```

| Tab | 功能 | 對應模組 |
|-----|------|---------|
| **搜尋** | 對話式找商機 | M5 |
| **名片庫** | 所有聯絡人列表/詳情 | M3 |
| **收錄** | 連拍 / 貼連結 / 掃 QR（M2 核心） | M2 |
| **待確認** | 姓名/公司/抬頭最低確認 | M2 |
| **我的** | 帳號、隱私、設定 | M1, M7 |

**收錄 Tab 視覺**：中央略突出（FAB 造型），展覽場景一鍵觸達。

### 2.2 預設 Tab 邏輯

| 使用者狀態 | 預設 Tab | 理由 |
|-----------|---------|------|
| 新用戶（0 張名片） | **收錄** | 先收資料 |
| OCR 完成 ≥3 張，尚未搜尋 | **搜尋**（+ Aha modal） | DDR-10 aha moment |
| 有待確認 >0 | **待確認**（badge 數字） | 但不阻擋搜尋 |
| 一般使用 | **搜尋** | 事件驅動，需要時找商機 |

### 2.3 桌面版（≥1024px）

```
┌──────────┬─────────────────────────────────────┐
│ Sidebar  │  Main Content                        │
│ · 搜尋   │                                      │
│ · 名片庫 │  （列表 + 詳情 split view）           │
│ · 收錄   │                                      │
│ · 待確認 │                                      │
│ · 我的   │                                      │
└──────────┴─────────────────────────────────────┘
```

- 搜尋 + 結果：左對話、右結果列表（或上下 split）
- 名片庫：左列表、右詳情面板
- 收錄：中央 modal 或 dedicated panel

---

## 3. 色彩系統

### 3.1 CSS Variables（Light Mode — 預設，展覽戶外可讀）

```css
:root {
  /* Brand */
  --color-primary:        #0F4C5C;   /* 深青綠 — 信任、商務 */
  --color-primary-hover:  #0B3A47;
  --color-primary-muted:  #E6F2F5;

  /* Action — 收錄/主要 CTA */
  --color-accent:         #D97706;   /* 琥珀 — 拍照快门感 */
  --color-accent-hover:   #B45309;
  --color-accent-muted:   #FEF3C7;

  /* Neutrals */
  --color-bg:             #FAFAF9;   /* 暖白 */
  --color-surface:        #FFFFFF;
  --color-surface-raised: #FFFFFF;
  --color-border:         #E7E5E4;
  --color-text-primary:   #1C1917;
  --color-text-secondary: #57534E;
  --color-text-tertiary:  #A8A29E;

  /* Semantic */
  --color-success:        #059669;
  --color-warning:        #D97706;
  --color-error:          #DC2626;
  --color-info:           #0284C7;

  /* AI 資訊分層 — 關鍵視覺語言 */
  --color-ai-bg:          #EFF6FF;   /* 原名片資料：白/.surface */
  --color-ai-border:      #BFDBFE;
  --color-ai-text:        #1E40AF;
  --color-ai-badge:       #DBEAFE;

  /* 隱私 */
  --color-privacy-bg:     #F0FDF4;
  --color-privacy-text:   #166534;

  /* OCR 信心度 */
  --color-confidence-high:   #059669;
  --color-confidence-medium: #D97706;
  --color-confidence-low:    #DC2626;
}
```

### 3.2 Dark Mode（P1，結構預留）

```css
[data-theme="dark"] {
  --color-bg:             #1C1917;
  --color-surface:        #292524;
  --color-text-primary:   #FAFAF9;
  --color-primary:        #2DD4BF;
  --color-accent:         #FBBF24;
  --color-ai-bg:          #1E3A5F;
  /* ... */
}
```

### 3.3 色彩使用規則

| 元素 | 色彩 |
|------|------|
| 主按鈕（確認、搜尋） | `--color-primary` |
| **收錄 / 拍照快门** | `--color-accent` |
| AI 補全欄位背景 | `--color-ai-bg` + 左側 3px `--color-ai-border` |
| 原始 OCR 欄位 | `--color-surface`（無 AI 色條） |
| 低信心欄位 | 欄位旁橘點 `--color-warning` |
| 隱私提示條 | `--color-privacy-bg` |
| 待確認 badge | `--color-warning` |

---

## 4. 字體系統

### 4.1 Font Stack

| 用途 | 字體 | Fallback |
|------|------|----------|
| 中文內文 | **Noto Sans TC** | PingFang TC, sans-serif |
| 英文/數字 UI | **Outfit** | system-ui, sans-serif |
| 資料/電話/Email | **JetBrains Mono** | monospace |

> 選擇理由：Noto Sans TC 繁中可讀性佳；Outfit 現代幹练非 Inter；Mono 用於聯絡方式易複製辨識。

### 4.2 Type Scale（base 16px, 1.25 ratio）

| Token | Size | Weight | 用途 |
|-------|------|--------|------|
| `--text-display` | 28px | 600 | 空狀態標題 |
| `--text-h1` | 24px | 600 | 頁面標題 |
| `--text-h2` | 20px | 600 | 區塊標題 |
| `--text-h3` | 18px | 500 | 卡片姓名 |
| `--text-body` | 16px | 400 | 內文 |
| `--text-body-sm` | 14px | 400 | 次要資訊 |
| `--text-caption` | 12px | 400 | 標籤、badge |
| `--text-mono` | 14px | 400 | 電話、Email |

行高：中文 1.6；英文 UI 1.5

---

## 5. 間距與佈局

### 5.1 Spacing Scale（4px base）

```
--space-1:  4px
--space-2:  8px
--space-3:  12px
--space-4:  16px
--space-5:  20px
--space-6:  24px
--space-8:  32px
--space-10: 40px
--space-12: 48px
```

### 5.2 佈局常數

| Token | 值 | 用途 |
|-------|-----|------|
| `--page-padding-x` | 16px (mobile) / 24px (desktop) | 頁面左右 |
| `--card-radius` | 12px | 卡片圓角 |
| `--btn-radius` | 8px | 按鈕 |
| `--input-radius` | 8px | 輸入框 |
| `--touch-min` | 44px | 最小觸控區（WCAG） |
| `--bottom-tab-height` | 56px + safe-area | 底部導航 |
| `--max-content-width` | 720px | 搜尋/收錄單欄上限 |

---

## 6. 核心元件庫

### 6.1 Button

| 變體 | 樣式 | 用途 |
|------|------|------|
| **Primary** | 填色 primary | 確認、送出搜尋 |
| **Accent** | 填色 accent | **拍照/收錄** |
| **Secondary** | 描邊 primary | 取消、次要 |
| **Ghost** | 無底 | 跳過、稍後 |
| **Destructive** | 填色 error | 刪除 |

高度：48px（mobile 主要）；36px（compact）

### 6.2 Contact Card（名片庫列表項）

```
┌─────────────────────────────────────────┐
│ [頭像/公司縮写]  王小明                    │
│                 ABC Tech · OEM 業務經理  │
│                 🔒 私人  ·  Computex 2026 │
│  ┌─ AI 摘要 ─────────────────────────┐  │
│  │ 工業電腦、嵌入式系統（AI 補全 · 82%）│  │
│  └─────────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### 6.3 AI Provenance Badge（平台標準）

所有 AI 生成/推估內容必須附：

```
┌──────────────────────┐
│ ✦ AI 補全 · 官網 · 82% │  ← 可點展開來源
└──────────────────────┘
```

- `AI 補全` — M6 公司資料
- `AI 推估` — 個人負責業務
- 信心 < 60%：badge 改 warning 色 + 「不確定」

### 6.4 Privacy Strip（常駐）

首頁/搜尋/收錄頂部 slim bar（可收起）：

```
🔒 你的名片預設私人，不會被公開搜尋
```

### 6.5 Confidence Dot（OCR 待確認）

| 信心 | 視覺 |
|------|------|
| ≥ 0.8 | 無 dot |
| 0.5–0.79 | 橘点 |
| < 0.5 | 紅点 + placeholder「待確認」 |

### 6.6 Search Input（M5 預告，平台級）

對話式輸入框 — 全平台統一：

```
┌─────────────────────────────────────────┐
│ 💬 我手上有誰做工業電腦的？               │
│                              [送出 →]   │
└─────────────────────────────────────────┘
```

- 多行 textarea，單行起始
- placeholder **中性固定文案**（MVP）；Pro 個人化範例見 M5 UIUX §2.1 / DDR-71

### 6.7 Toast / Banner

| 類型 | 位置 | 持續 |
|------|------|------|
| Success | top | 3s auto dismiss |
| Warning（duplicate） | top | 5s + action |
| Error | top | manual dismiss |
| Background job | bottom above tab | persistent until done |

### 6.8 Empty State Template

```
        [illustration: 簡线名片+放大鏡]
        
        {標題：一句話價值}
        {副標：具體下一步}
        
        [ Primary CTA ]
        [ Ghost 次要 ]
```

---

## 7. 互動與動效

### 7.1 Loading 策略

| 情境 | 模式 |
|------|------|
| 拍照上傳 | 底部 progress pill「上傳中 3/5」 |
| OCR 背景 | 卡片上 shimmer badge「辨識中」 |
| 搜尋 | 對話 bubble typing indicator |
| 列表首次載入 | skeleton cards × 5 |
| 按鈕 submit | spinner in-button |

### 7.2 動效原則

- Duration：150ms（micro）、250ms（panel）、350ms（page）
- Easing：`cubic-bezier(0.4, 0, 0.2, 1)`
- 連拍：快门 flash 100ms + 缩略图飛入底部 strip
- 待確認 swipe：Tinder-style 右滑確認、左滑跳過

### 7.3 手勢（Mobile）

| 手勢 | 動作 |
|------|------|
| 長按卡片 | 快速預覽 |
| 右滑待確認 | 確認 |
| 左滑待確認 | 跳過 |
| 下拉列表 | refresh |

---

## 8. 無障礙（WCAG 2.1 AA）

- 對比度：正文 ≥ 4.5:1；大字 ≥ 3:1
- 觸控目標 ≥ 44×44px
- 所有 icon button 需 `aria-label`
- AI badge 需 screen reader 讀出「AI 推估，信心 82%」
- 搜尋輸入支援 keyboard navigation
- 不僅靠色彩傳達信心度（dot + 文字）

---

## 9. 平台級文案語氣

| 情境 | 語氣 | 範例 |
|------|------|------|
| 收錄成功 | 簡短肯定 | 「已收進名片庫 ✓」 |
| AI 不確定 | 誠實 | 「資訊不足，建議確認公司名稱」 |
| 錯誤 | 具體+下一步 | 「連結格式不支援，請改貼連結或手動新增」 |
| 空狀態 | 價值導向 | 「拍 3 張名片，立刻試試 AI 搜尋」 |
| 隱私 | 安心 | 「預設私人，只有你看得到」 |

避免：「請完善資料」「您尚未設定業務方向」等責備式文案。

---

## 10. Logo 與品牌標記（MVP 佔位）

- **Wordmark**：BSChat（Outfit SemiBold）
- **App Icon 概念**：名片轮廓 + 对话气泡交集；主色 primary + accent 點綴
- **Favicon**：BC  monogram

---

## 11. 設計交付物清單

| 文件 | 內容 |
|------|------|
| 本文件 | 平台設計基礎 |
| `BSChat_PM_M2.md` | M2 PM L3（sub-features、rules、handoff） |
| `BSChat_PM_M3.md` | M3 聯絡人結構化 PM L3 |
| `BSChat_PM_M5.md` | M5 AI 搜尋 PM L3 |
| `BSChat_PM_M6.md` | M6 公司補全 PM L3 |
| `BSChat_SA-SD_M2.md` | M2 架構 / API / Handoff 契約 |
| `BSChat_SA-SD_M5.md` | M5 AI 搜尋架構 / API / 检索 |
| `BSChat_UIUX_M2.md` | M2 模組流程 + 線框 |
| `BSChat_UIUX_M3.md` | M3 聯絡人詳情 + 三區塊 |
| `BSChat_UIUX_M6.md` | M6 公司補全 UI + Pro 設定 |
| `BSChat_UIUX_M5.md` | M5 搜尋對話介面 + 結果卡 |
| `BSChat_ENG_M5.md` | M5 AI 搜尋實作 + Sprint tickets |
| `BSChat_QA_M5.md` | M5 AI 搜尋測試案例 |
| `BSChat_TECH_STACK.md` | **实作技术栈权威**（PWA + features/shared · v1.1 待确认） |

---

*Design Foundation v1.0 — SDLC Phase 1 UI/UX*
