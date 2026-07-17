# BSChat ENG — 企業租戶完整 B

> **版本**：v1.0 · 2026-07-16  
> **依據**：SA-SD／UIUX enterprise B、TECH_STACK  
> **估算**：~2–3 工程日  
> **MVP 簡化**：成員電子名片草稿可第二波；第一波 Admin 代建名片即可業務測

---

## Delta check（ENG）

已檢查 SA-SD enterprise B、UIUX、既有 `team_invite`／`m11`／`OrgAdminPage`／密碼進場  
→ ✅ 開工 ENG

---

## 1. 依賴

無新套件。環境變數：`ENTERPRISE_OPS_TOKEN`（營運開通）。

---

## 2. 後端清單

| 檔案 | 動作 |
|------|------|
| `alembic/versions/022_enterprise_tenant_b.py` | orgs 欄位、applications、invites.kind／email、members.plan_before |
| `models/organization.py` 等 | 欄位 |
| `modules/enterprise/`（新） | provision、approve、invite、remove、transfer、B1 helpers |
| `api/v1/enterprise.py`（新） | 申請／Admin API |
| `api/v1/ops_enterprise.py`（新） | provision／approve／reject |
| `modules/team_invite/service.py` | 企業 org 禁止當席次的舊 invite；或導向 enterprise 模組 |
| `m11/.../deps.py` | publish 改 **primary admin** 閘 |
| `schemas/` | 對應 Pydantic |
| `scripts/provision_enterprise.py` | CLI 包一層 ops（方便 dogfood） |
| `tests/test_enterprise_tenant_b.py` | 開通、邀請、B1、移除降級、非 Admin 403 |

### B1 偽碼

```python
async def accept_enterprise_seat(db, user, invite):
    assert invite.invite_kind == "enterprise_seat"
    if invite.invited_email and user.email.lower() != invite.invited_email.lower():
        raise 403 INVITE_EMAIL_MISMATCH
    # seat_limit check
    if member.plan_before_enterprise is None:
        member.plan_before_enterprise = user.entitlement.plan_tier
    apply_plan_preset(user.entitlement, "enterprise")
    ensure member role=member
```

---

## 3. 前端清單

| 檔案 | 動作 |
|------|------|
| `app/(auth)/enterprise/apply/page.tsx` | 申請表 |
| `app/(auth)/join/enterprise/[token]/page.tsx` | 企業邀請 |
| `features/enterprise/` | api／hooks／ApplyForm |
| `features/org/OrgAdminPage.tsx` | 成員／邀請／轉移 Tab |
| `features/settings/SettingsPage.tsx` | 企業後台入口、申請狀態 |
| types | org is_enterprise、memberships |

---

## 4. 實作序

1. Migration + provision API + 測試開通  
2. 企業邀請 accept＋B1＋測試  
3. 成員列表／移除／轉移  
4. 申請表＋ops approve  
5. 前端 Admin／join／settings  
6. 收緊 M11 primary admin  
7. Dogfood：註冊 Admin → provision → 邀業務  

---

## 5. 測試要點

| ID | Expect |
|----|--------|
| T1 | provision 後 admin 為 enterprise＋primary |
| T2 | 非 primary 發 enterprise 邀請 403 |
| T3 | accept 後成員 enterprise；email 不符 403 |
| T4 | remove 後方案還原／free；不可 publish |
| T5 | 無 ops token provision 401 |

---

## 6. 完成標準
- [x] 清單與序清楚  
- [x] Code（2026-07-16）：migration 022、APIs、FE、`test_enterprise_tenant_b` 4 passed  
