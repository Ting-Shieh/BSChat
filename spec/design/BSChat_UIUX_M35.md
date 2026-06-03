# BSChat UI/UX — Module 3.5：個人 LinkedIn 補充

> **依據**：`BSChat_PM_M35.md`、`BSChat_Design_Foundation.md`（AI 透明）  
> **狀態**：UI/UX L3 ✅ 可鎖定

---

## 1. 设计原则

1. **Free 不羞辱**：永远可见 M3 AI 推估；LinkedIn 为 Pro **增值**，非「Free 不准」
2. **AI 透明**：LinkedIn 区必须标注「公开资料 · AI 整理 · 信心 · 日期」
3. **宁缺勿滥**：match 不确定 → 候选确认 UI，不静默写错
4. **不混淆 OCR**：职称仍在「名片原文」；LinkedIn 在 `ai_inferred.person_scope`

---

## 2. 详情页 — ai_inferred 区状态

| 状态 | Free | Pro |
|------|------|-----|
| 仅 M3 推估 | 显示 ResponsibilityBlock | 同左 + 可选 LinkedIn CTA |
| M3.5 pending | — | skeleton「正在整理 LinkedIn 公开资料…」 |
| M3.5 成功 | — | PersonScopeBlock 主显；M3 折叠 |
| needs_confirmation | — | DisambiguationSheet |
| M3.5 rejected | — | 隐藏 LinkedIn 区；M3 仍可见 |
| M3.5 failed | — | inline「找不到公开资料」+ 重试（扣 quota） |

### 2.1 Free — 升级 CTA

```
┌─────────────────────────────────────────┐
│ 🔒 Pro：LinkedIn 公開資料核對            │
│ 比 AI 推估更準地確認對方負責範圍          │
│              [ 了解 Pro ]                │
└─────────────────────────────────────────┘
```

- 不使用 lock 图标刺激过强；可用 `Pro` badge
- 点击 → 升级 modal（不跳转外链支付 MVP 可 stub）

### 2.2 Pro — PersonScopeBlock

```
┌─ 職場公開資料 ───────────────────────────┐
│ ▎目前：OEM Sales Manager · ABC Tech      │
│ ▎可能負責：工業級 SSD 通路與 SI 伙伴      │
│                                          │
│ ✦ LinkedIn 公開資料 · AI 整理 · 82%     │
│ 更新於 2026-05-20                        │
│                                          │
│ [ 重新查詢 ]  [ 不是此人 ]                 │
└─────────────────────────────────────────┘
▸ 備用：AI 推估（來自名片）· 67%
```

**视觉**：沿用 `--color-ai-bg`；左侧色条区分 M3（蓝） vs M3.5（可略深或加 LinkedIn 中性 icon，**不用** LinkedIn 品牌色侵权）

### 2.3 消歧 Sheet

```
找到多位可能匹配
请确认是否同一人（避免写错资料）

( ) 王小明 · ABC Tech · OEM Manager     87%
( ) 王小明 · ABC Technology · Sales    72%

[ 确认所选 ]  [ 都不是 ]  [ 取消 ]
```

---

## 3. 手动触发入口

| 位置 | 组件 | 文案 |
|------|------|------|
| 详情 ai_inferred footer | Button secondary | 「LinkedIn 补充（本月剩 n 次）」 |
| M5 SearchResultCard overflow | Menu item | 「深入查此人 · LinkedIn」 |
| quota=0 | disabled + tooltip | 「本月额度已用完」 |

**loading**：按钮内 spinner；不阻塞详情其他区块操作

---

## 4. 列表页 AI 摘要优先级（Pro）

1. `person_scope`（conf≥0.75，M3.5 active）
2. `responsibility_scope`（M3，conf≥0.6）
3. M6 `company_products_preview`

Free：跳过 1，逻辑不变。

---

## 5. 设置页（Pro）

```
LinkedIn 个人补充
  [x] 名片含 LinkedIn 链接时自动补充
  本月已用：3 / 20
```

---

## 6. 空态与错误

| 错误 | 文案 |
|------|------|
| NO_CANDIDATES | 「找不到公开的 LinkedIn 资料，可稍后再试或仅参考 AI 推估。」 |
| QUOTA_EXCEEDED | 「本月 LinkedIn 补充次数已用完。」 |
| NEEDS_CONFIRM | 「请确认是否为同一人。」 |

---

## 7. Accessibility

- PersonScopeBlock：`aria-label="LinkedIn 公开资料整理，信心 82%，可能负责…"`
- 候选列表：radio group + 明确 label

---

*UI/UX M3.5 v1.0*
