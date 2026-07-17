# BSChat QA — M1 公開推薦終身試用（切片）

> **版本**：v1.0  
> **日期**：2026-07-14  
> **依據**：`BSChat_SA-SD_M1.md`、`BSChat_ENG_M1.md`、PRD v4 US-v4-5  

---

## Delta check（M1 · QA）

已檢查 SA-SD（01/02＝A）、ENG 測試表、實作單元測試 7 passed  
→ ✅ QA 案例對齊

---

## 自動化

| 套件 | 狀態 |
|------|------|
| `tests/test_m1_public_recommend_trial.py` | 扣次／用盡／Pro／升降級保留 used |
| `tests/test_m5b_public_search.py::test_m5b_free_network_forbidden_when_trial_exhausted` | 用盡 → 403 |

## 手動煙測

1. Migration `019_public_recommend_trial`  
2. Free 登入 →「我的」顯示剩 2／2  
3. 有公開池時 `scope=all` 搜尋兩次 → 剩餘 0；第三次 Plan 步驟 3 略過  
4. 池空時搜尋 → 剩餘不變、步驟 3「沒有可推薦」  
5. Pro → 顯示無限、used 不增  

## 通過標準

- [x] 單元測試綠  
- [ ] 手動煙測（部署／本機 DB 後）  
