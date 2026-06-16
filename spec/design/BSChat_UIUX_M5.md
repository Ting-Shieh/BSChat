# BSChat UI/UX — Module 5：AI 搜尋（對話式找商機）

> **依據**：M5 PM L3 v1.1、M5 SA/SD v1.0、`BSChat_Design_Foundation.md`、M3 UI/UX v1.0  
> **核心 UX 目標**：**10 分鐘內 Aha** — 用一句話找到「公司對、人對」的窗口，並**說清楚為何符合**

---

## 1. M5 使用者流程

### 1.1 首次搜尋 — Aha Moment（Happy Path）

```mermaid
flowchart TD
    A[OCR ≥3 張完成] --> B[預設切換搜尋 Tab]
    B --> C[GET /search/status]
    C --> D[顯示範例 query + 輸入框]
    D --> E[使用者輸入自然語言]
    E --> F[POST /search/queries]
    F --> G{status}
    G -->|COMPLETED| H[結果列表 + match_reason]
    G -->|EMPTY| I[空結果引導]
    H --> J{aha_moment?}
    J -->|是| K[Aha Modal]
    J -->|否| L[使用者瀏覽結果]
    H --> M[點結果 → M3 詳情 + Context Banner]
    M --> N[M8 複製電話/Email]
```

### 1.2 一般搜尋（事件驅動）

```mermaid
flowchart TD
    A[搜尋 Tab] --> B[輸入新 query]
    B --> C[Typing indicator 1–3s]
    C --> D[結果替換上一輪]
    D --> E{使用者行動}
    E -->|點卡片| F[詳情 + 符合原因]
    E -->|複製聯絡| G[M8 Toast]
    E -->|換問法| B
    E -->|去收錄| H[收錄 Tab]
```

### 1.3 空結果（不放棄）

```mermaid
flowchart TD
    A[POST /search/queries] --> B{empty_state.reason}
    B -->|NO_INDEXED_CONTACTS| C[「先收錄幾張名片」+ CTA 收錄]
    B -->|NO_MATCH| D[換問法建議 + 範例 query]
    B -->|indexed 1–2| E[hint「再多收幾張更準」+ 仍可搜]
    C --> F[收錄 Tab]
    D --> G[保留輸入框 focus]
```

### 1.4 從結果進入詳情（M3 整合）

```mermaid
flowchart LR
    A[SearchResultCard] --> B[點擊]
    B --> C["/contacts/:id?from_search=:queryId"]
    C --> D[M3 詳情頂部 Context Banner]
    D --> E[符合原因全文 + 來源字段 chips]
    E --> F[使用者審核 → M8 聯絡]
```

### 1.5 深入查詢 — Live Augment（P1 · DDR-34）

```mermaid
flowchart TD
    A[結果頁 suggest_live 或 按鈕] --> B{live quota}
    B -->|OK| C[POST live-augment]
    B -->|用盡| D[Quota Dialog + Pro CTA]
    C --> E[結果卡 ⏳ 即時查詢中]
    E --> F[GET poll → live_products merge]
    F --> G[标注「即時查詢」于 match_reason]
    G --> H{使用者}
    H -->|採用| I[Adopt Dialog → M6 cache]
    H -->|僅參考| J[離開]
```

### 1.6 Phase 3 預留（不阻塞 MVP）

- Pool B 公開商務池：结果卡标注「BSChat 公開商務池 · {公司}」
- MVP UI **不**显示 scope 切换器

---

## 2. 畫面線框

### 2.1 搜尋 Tab — 就緒態（Mobile）

```
┌─────────────────────────────────────┐
│ 🔒 你的名片預設私人，不會被公開搜尋   │  ← Privacy Strip（可收起）
├─────────────────────────────────────┤
│  找商機                              │
│  用一句話描述你現在要找什麼           │
├─────────────────────────────────────┤
│  ┌─────────────────────────────────┐  │
│  │ 💬 用自然語言描述你要找的人…     │  │  ← SearchInput textarea（中性 placeholder）
│  │                                 │  │
│  │                      [搜尋]     │  │  ← Primary；Enter 送出
│  └─────────────────────────────────┘  │
│  5 位可搜尋 · 今日剩餘 28 次          │  ← indexed_count（Pool A）；MVP 文案不用「已索引」
├─────────────────────────────────────┤
│         （尚無結果 — 留白）           │
├─────────────────────────────────────┤
│  🔍    📇    [➕]    ✓    👤        │
└─────────────────────────────────────┘
```

**indexed_count < 3**：
- 输入框**仍可用**（不 disable）
- caption 改「已收錄 2 位 · 再多收幾張，搜尋會更準」
- **不顯示**通用靈感 chips（DDR-71）

**Pro P1（F-5.17）**：搜尋按鈕下方可顯示 **1–3 個個人化建議 pill**（依已索引名片的公司產品、場合標籤推導）；點擊**只填入**輸入框，不自動送出（避免誤觸額度）。

---

### 2.2 搜尋 Tab — 載入中

```
┌─────────────────────────────────────┐
│  ... Privacy Strip ...               │
├─────────────────────────────────────┤
│  ┌─────────────────────────────────┐  │
│  │ 我手上有誰做 IPC 的？      [···] │  │  ← 已送出 query 固定显示
│  └─────────────────────────────────┘  │
├─────────────────────────────────────┤
│  ┌─ 助手 ─────────────────────────┐  │
│  │  ● ● ●  正在比對你的名片庫…     │  │  ← typing indicator
│  └─────────────────────────────────┘  │
├─────────────────────────────────────┤
│  ┌ skeleton SearchResultCard × 3 ┐  │
└─────────────────────────────────────┘
```

- 送出后：**输入框保留 query 文字**，按钮 in-spinner
- 禁止重复送出（debounce + disabled）

---

### 2.3 搜尋 Tab — 有結果（核心）

```
┌─────────────────────────────────────┐
│  ... Privacy Strip ...               │
├─────────────────────────────────────┤
│  ┌ QueryBubble ────────────────────┐  │
│  │ 我手上有誰做 IPC 的？             │  │  ← 用户 query，右对齐浅底
│  └─────────────────────────────────┘  │
│  ┌ AssistantBubble ────────────────┐  │
│  │ 找到 3 位可能符合的聯絡人          │  │
│  │ degraded 时：小字「简化排序模式」   │  │
│  └─────────────────────────────────┘  │
├─────────────────────────────────────┤
│  ┌ SearchResultCard #1 ────────────┐  │
│  │ [縮圖]  王小明          未確認     │  │  ← review badge
│  │         ABC Tech                  │  │
│  │         OEM 業務經理               │  │
│  │  ┌─ 符合原因 ──────────────────┐  │  │
│  │  │ 公司主要產品包含工業電腦主機；   │  │  ← match_reason 主视觉
│  │  │ 職稱為 OEM 業務經理            │  │  │
│  │  └──────────────────────────────┘  │  │
│  │  🏷 Computex 2026                  │  │  ← source_label if in match
│  │  [📋 複製電話]  [✉️ 複製 Email]    │  │  ← M8 P0
│  │                          [查看 →]  │  │
│  └───────────────────────────────────┘  │
│  ┌ SearchResultCard #2 ────────────┐  │
│  │ ...                               │  │
│  └───────────────────────────────────┘  │
├─────────────────────────────────────┤
│  ┌─ 換個問法？ ─────────────────────┐  │  ← P1 refinement_suggestions
│  │ · 只要 OEM 通路的                 │  │
│  │ · 限定 Computex 2026              │  │
│  └───────────────────────────────────┘  │
├─────────────────────────────────────┤
│  ┌ SearchInput（可追問 P1）─────────┐  │
│  │ 💬 再問一個問題…          [送出]   │  │
│  └─────────────────────────────────┘  │
└─────────────────────────────────────┘
```

**SearchResultCard 层级**：
1. **match_reason**（必显，≥2 行 clamp 可展开）
2. 姓名 / 公司 / 职称
3. M8 行动按钮
4. AI 推估来源若含 responsibility：chip「AI 推估 · 67%」

**rank 不显示数字** — 避免「排名第几」的 CRM 感；顺序即优先级。

---

### 2.4 搜尋 Tab — 空結果

**NO_MATCH**：
```
┌─────────────────────────────────────┐
│  ┌ QueryBubble ────────────────────┐  │
│  │ 我手上有誰做量子計算的？          │  │
│  └─────────────────────────────────┘  │
│  ┌ AssistantBubble ────────────────┐  │
│  │ 目前名片庫裡沒有找到符合的聯絡人    │  │
│  │ 這不代表你沒收過 — 試試換個說法    │  │
│  └─────────────────────────────────┘  │
│        [illustration: 放大鏡+名片]     │
│  試試這樣問：                          │
│  · 我手上有誰做工業電腦的？             │
│  · 我手上有誰做嵌入式系統的？           │
│  [ 再搜一次 ]          [ 去收錄名片 ]   │
└─────────────────────────────────────┘
```

**NO_INDEXED_CONTACTS**：
```
│  還沒有可搜尋的名片                  │
│  先收錄 3 張，立刻試試 AI 搜尋         │
│  [ 開始收錄 ]                        │
```

**文案原则（DDR-55）**：不责备用户「你还没录入够」；用「试试换说法 / 去收录」引导。

---

### 2.5 Aha Moment Modal

**触发**：`aha_moment: true`（首次 search COMPLETED 且 result_count ≥ 1）

```
┌─────────────────────────────────────┐
│              ✨                      │
│     找到了！                         │
│  這就是 BSChat 的用法 —              │
│  用對話從名片庫找出商機               │
│                                      │
│  [ 查看結果 ]    [ 繼續收錄更多 ]     │
└─────────────────────────────────────┘
```

- 仅显示**一次**（localStorage `aha_dismissed`）
- 「繼續收錄更多」→ 收錄 Tab
- 不阻塞；可点 backdrop 关闭

---

### 2.6 桌面版（≥1024px）— Split View

```
┌──────────┬────────────────────┬─────────────────────────┐
│ Sidebar  │  對話區           │  結果區                  │
│ · 搜尋 ● │                   │                         │
│ · 名片庫 │  QueryBubble      │  SearchResultCard × N   │
│ · 收錄   │  AssistantBubble  │  （可 scroll）           │
│ · 待確認 │  SearchInput      │                         │
│ · 我的   │  SearchInput      │  點卡片 → 右側或 overlay │
│          │                   │  詳情（M3 split）        │
└──────────┴────────────────────┴─────────────────────────┘
```

- 结果区固定宽 420px；对话区 flex
- 点「查看」→ 名片库 split 打开详情，**保留搜尋上下文**

---

### 2.7 M3 詳情 — Search Context Banner（M5 → M3）

```
┌─────────────────────────────────────┐
│  ← 返回搜尋結果                      │
├─────────────────────────────────────┤
│  ┌─ 搜尋符合原因 ───────────────────┐  │
│  │ 公司主要產品包含工業電腦主機；     │  │
│  │ 職稱為 OEM 業務經理               │  │
│  │ [工業電腦主機] [OEM 業務經理]     │  │  ← match_sources chips
│  └──────────────────────────────────┘  │
│  ... M3 詳情三區塊 ...                 │
└─────────────────────────────────────┘
```

- 背景：`--color-primary-muted`
- 仅当 `from_search` query param 存在时显示
- 「返回搜尋結果」→ 搜尋 Tab + scroll 到对应 card（`queryId` + `contactId` hash）

---

### 2.8 P1 — Live Augment Banner

**触发**：`suggest_live: true` 或用户点「深入查詢」

```
┌─────────────────────────────────────┐
│  💡 部分結果的資料可能較舊            │
│  [ 深入查詢最新公司資訊 ]  本月剩 4 次 │
└─────────────────────────────────────┘
```

**结果卡 live 态**：
```
│  ┌─ 符合原因 ──────────────────────┐  │
│  │ ...；本次查詢：嵌入式系統（即時）  │  │  ← badge「即時查詢」
│  └─────────────────────────────────┘  │
│  [ 採用並儲存到公司資訊 ]              │  → M6 query_adopt
```

---

## 3. 元件規格

### 3.1 `SearchInput`

| 属性 | 规则 |
|------|------|
| 类型 | `<textarea rows={2} maxLength={2000}>` |
| placeholder | **中性固定文案**（MVP）；Pro P1 可輪播 `sample_queries`（個人化） |
| 靈感 pills | **MVP 不渲染**；Pro P1 見 §2.1 |
| 送出 | Primary button；`Cmd/Ctrl+Enter` |
| 禁用 | loading 中；429 quota |
| 高度 | min 56px；max 120px auto-grow |

### 3.2 `QueryBubble` / `AssistantBubble`

| 元件 | 对齐 | 背景 |
|------|------|------|
| QueryBubble | 右 | `--color-surface-elevated` |
| AssistantBubble | 左 | transparent；typing 时 ●●● |

### 3.3 `SearchResultCard`

| 元素 | 数据源 | 规则 |
|------|--------|------|
| 缩图 | contact_preview.image_url | 无则 avatar |
| 未确认 badge | review_status | `unconfirmed` 显示 |
| match_reason | results[].match_reason | 主区块；可展开 |
| source chip | source_label | 若有 |
| AI chip | match_sources | field=responsibility_scope 时 |
| 复制按钮 | phones[0], emails[0] | M8；无则 hide |
| 查看 | navigate |带 from_search |

**点击区域**：整卡 → 详情；复制按钮 stopPropagation。

### 3.4 `SearchEmptyState`

| prop | 值 |
|------|-----|
| reason | NO_INDEXED_CONTACTS \| NO_MATCH \| LOW_INDEX_COUNT |
| suggestions | string[] |
| sample_queries | string[]；**MVP API 回 `[]`、UI 不顯示**；Pro P1 用於個人化 pills |
| cta | capture \| retry |

### 3.5 `AhaMomentModal`

| prop | 规则 |
|------|------|
| open | aha_moment && !dismissed |
| onDismiss | set localStorage |

### 3.6 `SearchQuotaBanner`（429 / 403）

```
今日搜尋次數已用完（30/30）· 明天重置    [ 了解 Pro ]
本月即時查詢已用完（5/5）· [ 升級 Pro ]
```

---

## 4. 狀態與 API 映射

| API status | UI |
|------------|-----|
| loading | typing + skeleton |
| COMPLETED | ResultCard list |
| EMPTY | SearchEmptyState |
| FAILED | Error banner + 重试 |
| degraded: true | AssistantBubble 小字 + 仍显示结果 |
| suggest_live: true | LiveAugmentBanner（P1） |
| aha_moment: true | AhaMomentModal |

| empty_state.reason | 标题 | Primary CTA |
|--------------------|------|-------------|
| NO_INDEXED_CONTACTS | 還沒有可搜尋的名片 | 開始收錄 |
| NO_MATCH | 目前沒找到符合的 | 去收錄名片（Ghost）+ 换问法 |
| LOW_INDEX_COUNT | hint only | 无 blocking |

---

## 5. 互動與動效

### 5.1 Loading

| 情境 | 模式 |
|------|------|
| 首次 POST search | Assistant typing ●●● + skeleton × 3 |
| 结果返回 | cards stagger fade-in 150ms × rank |
| live augment（P1） | 卡内 pulse「查詢中…」 |
| GET /search/status | Tab 级 skeleton 仅首次 |

### 5.2 微互动

| 动作 | 反馈 |
|------|------|
| 送出 search | 输入框 blur；scroll to results |
| 复制成功 | Toast「已複製」3s |
| Aha modal 关闭 | confetti 轻量 1s（optional P1） |
| 点 sample query | 填入输入框 + focus |
| adopt live（P1） | Toast「已更新公司資訊」+ M6 详情 sync |

### 5.3 乐观更新

- Search：**不** optimistic results；等 API 200
- 复制：**可** optimistic Toast（clipboard API 失败 rollback）

---

## 6. 錯誤狀態

| 情境 | UI | code |
|------|-----|------|
| cache quota 用尽 | SearchQuotaBanner + disable 送出 | SEARCH_QUOTA_EXCEEDED 429 |
| live quota 用尽 | Quota Dialog | LIVE_QUOTA_EXCEEDED 403 |
| LLM degraded | 小字 + 结果仍显示 | degraded: true |
| 503 | Full-width Error + 重试 | SERVICE_UNAVAILABLE |
| query 过长 | inline 错误 | QUERY_TOO_LONG 400 |
| index stale hint | caption「部分新名片同步中」 | optional API field |

---

## 7. 文案規範（M5）

| 情境 | 文案 | 避免 |
|------|------|------|
| 就绪 caption | 「已收錄 N 位 · 可搜尋」 | 「索引完成」 |
| loading | 「正在比對你的名片庫…」 | 「加载中」 |
| 有结果 | 「找到 N 位可能符合的聯絡人」 | 「匹配成功」 |
| match_reason 区标题 | 「符合原因」 | 「AI 推荐」 |
| AI 推估 | 「可能負責 …（AI 推估 · n%）」 | 肯定句 |
| empty NO_MATCH | 「試試換個說法」 | 「没有数据」 |
| Privacy | 「你的名片預設私人，不會被公開搜尋」 |  buried in settings |
| live badge | 「即時查詢」 | 「实时数据」 |
| adopt | 「採用並儲存到公司資訊」 | 「确认」 |
| Pro pitch | 「搜尋更多、查最新公司資料」 | 「解锁高级」 |

---

## 8. 無障礙

- `SearchInput`：`aria-label="描述你想找的商機"`；`aria-describedby` 指向 caption
- 送出中：`aria-busy="true"` on results region
- `SearchResultCard`：`role="article"`；`aria-labelledby={name}` + reason as description
- match_reason：`aria-label="符合原因：{text}"`
- 复制按钮：`aria-label="複製 {name} 的電話"`
- Aha modal：focus trap；Esc 关闭
- typing indicator：`aria-live="polite"`「正在搜尋」
- 键盘：Tab 顺序 Input → 结果卡 → 复制 → 查看；Enter on card = 查看

---

## 9. 与平台 / 跨模块整合

| 模块 | 整合点 |
|------|--------|
| **Design Foundation** | SearchInput §6.6、Privacy Strip、Empty Template、Tab 默认逻辑 |
| **M3** | Context Banner、`ContactListCard` 视觉一致、详情 from_search |
| **M6** | match_reason 引用 products；P1 adopt → M6 UI 更新 |
| **M8** | ResultCard 复制 CTA |
| **M2** | empty → 收錄 Tab；Aha → 继续收錄 |
| **M1** | quota banner、Pro CTA |

---

## 10. P1 / P2 交付分期

| 优先级 | UI 交付 |
|--------|---------|
| **P0** | Search Tab、Input、ResultCard、Empty、Aha、Context Banner、M8 复制 |
| **P1** | Live banner、adopt flow、refinement chips、多轮输入（session） |
| **P2** | 搜尋历史列表、桌面 split 优化 |
| **P3** | Pool B 来源标注、Pro 跨池 scope gate |

---

## 11. ENG 元件清单

| 元件 | 路径建议 |
|------|----------|
| `SearchPage` | `app/(tabs)/search/page.tsx` |
| `SearchInput` | `components/search/SearchInput.tsx` |
| `SearchResultCard` | `components/search/SearchResultCard.tsx` |
| `SearchEmptyState` | `components/search/SearchEmptyState.tsx` |
| `AhaMomentModal` | `components/search/AhaMomentModal.tsx` |
| `SearchContextBanner` | `components/contacts/SearchContextBanner.tsx` |
| `LiveAugmentBanner` | `components/search/LiveAugmentBanner.tsx` (P1) |
| `useSearchQuery` | `hooks/useSearchQuery.ts` — TanStack Query |

**Hooks**：
- `useSearchStatus()` — GET /search/status on Tab focus
- `useSearch()` — POST /search/queries mutation
- invalidate：收錄完成后 invalidate status

---

**M5 UI/UX v1.0：✅ 可锁定**

---

### 🤝 Handoff: UI/UX → ENG — Module 5：AI 搜尋

**State Tracker snapshot**：
| 模組 | PM | SA/SD | UI/UX | ENG | QA |
|------|:--:|:-----:|:-----:|:---:|:--:|
| M5 | ✅ v1.1 | ✅ v1.0 | ✅ v1.0 | ⏳ | ⏳ |

**ENG 必須实现（P0）**：
1. 搜尋 Tab + `GET /search/status` + `POST /search/queries`
2. `SearchResultCard` + match_reason 区块
3. `SearchEmptyState` 三种 reason
4. `AhaMomentModal`
5. M3 `SearchContextBanner` + from_search 路由
6. M8 复制 on ResultCard

**Open（不阻塞 ENG P0）**：P1 live/adopt UI、P2 历史、桌面 split  polish

---

*UI/UX M5 v1.0 — SDLC Phase 1*
