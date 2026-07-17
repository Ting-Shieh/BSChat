# BSChat ENG — M1 公開推薦終身試用（切片）

> **版本**：v1.0  
> **日期**：2026-07-14  
> **依據**：`BSChat_SA-SD_M1.md` v1.0、`BSChat_UIUX_M1.md` v1.0、`BSChat_TECH_STACK.md` LOCKED  
> **估算**：~0.5–1 工程日  
> **範圍**：entitlement 欄位 + 閘門 + `/me`／search status + 前端 Plan／設定；不做收款

---

## Delta check（M1 · ENG）

已檢查 PRD v4 §4（無變動）、SA-SD_M1（已鎖定 A/A）、UIUX_M1（剛完成）、TECH_STACK（LOCKED 無變動）  
→ ✅ 開工 ENG

---

## 1. 技術選型（增量）

無新依賴。沿用：Alembic、SQLAlchemy、FastAPI、Pydantic、TanStack Query、既有 `entitlements.py`。

---

## 2. 後端改動清單

| 檔案 | 動作 |
|------|------|
| `alembic/versions/019_public_recommend_trial.py`（或下一號） | 加兩欄 |
| `app/models/user.py` | `UserEntitlement` 欄位 |
| `app/core/entitlements.py` | `can_use_public_recommend` / `remaining_*` / `consume_public_recommend`；`apply_plan_preset` **不清** used |
| `app/schemas/auth.py` | `QuotaInfo` 擴充 |
| `app/api/v1/me.py` | `_build_me` 填新欄位 |
| `app/modules/m5_search/public_search.py` | deprecated wrapper → 呼叫 M1 |
| `app/modules/m5_search/service.py` | 閘門：池空不扣；有池且 Free 則 consume；403 文案 |
| `app/schemas/search.py` | `SearchStatus` 擴充 |
| `tests/test_m1_public_recommend_trial.py` | 單元／API：扣次、池空、用盡、Pro 不扣、降級保留 used |

### 扣次偽碼（對齊 SA-SD §3.3）

```python
include_public = scope in ("network", "all")
if include_public:
    if not can_use_public_recommend(ent):
        if scope == "network":
            raise HTTPException(403, "PUBLIC_RECOMMEND_TRIAL_EXHAUSTED")
        include_public = False  # all → degrade to private-only
    elif public_pool_count == 0:
        include_public = False  # 不扣
    else:
        await consume_public_recommend(db, ent)  # Free +1；Pro no-op
```

---

## 3. 前端改動清單

| 檔案 | 動作 |
|------|------|
| `shared/types/auth.ts` | `QuotaInfo` 新欄 |
| `shared/types/search.ts` | `SearchStatus` 新欄 |
| `features/settings/components/SettingsPage.tsx` | 試用列／無限／用盡 CTA |
| `features/search/components/SearchPage.tsx` | `includePublicPool` ← status／me，非僅 isPro |
| `features/search/components/SearchPlanPanel.tsx` | 略過 reason：trial／empty／ok |

---

## 4. Sprint 切片（建議實作序）

1. Migration + model + entitlements helpers + tests  
2. `/me` + search status + search service 閘門  
3. 前端 types + Settings + Search Plan  
4. 手動：Free 搜兩次含公開 → 第三次步驟 3 略過  

---

## 5. 測試要點

| ID | Given | Expect |
|----|-------|--------|
| T1 | Free used=0、池>0、scope=all | used→1；有公開檢索 |
| T2 | Free、池=0、scope=all | used 不變；僅私有 |
| T3 | Free used=2、scope=all | 不進公開；used=2 |
| T4 | Free used=2、scope=network | 403 |
| T5 | Pro、任意 | used 不變 |
| T6 | Free used=1 → 升 Pro → 降 Free | used 仍為 1 |

---

## 6. 完成標準

- [x] ENG 清單與偽碼對齊 SA/SD  
→ 接實作（Code）→ review → QA  
