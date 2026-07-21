# SA/SD — M5 多輪搜尋（DDR-v4-17）· 2026-07-21

> 補丁於 `BSChat_SA-SD_M5.md`：啟用原 P1 `search_sessions`。

## 資料

### `search_sessions`
| 欄位 | 說明 |
|------|------|
| id, user_id, workspace_id | PK／擁有者 |
| title | 首問截斷（≤80） |
| turn_count | 往來則數 |
| status | `active` \| `closed` |
| created_at, updated_at | |

### `search_queries`
- 新增可空 `session_id` → `search_sessions.id`
- 既有一列＝一則用戶提問（一 turn）

## API

| Method | Path | 說明 |
|--------|------|------|
| GET | `/search/sessions` | 最近對話串（標題＝首問） |
| GET | `/search/sessions/{id}` | 串內各 turn＋結果 |
| POST | `/search/queries` | `session_id?`：無則開新串；有則追問 |

Response 增補：`session_id`、`assistant_message?`、`follow_up_suggestions?`

> 瀏覽公開池：由 **LLM `intent_kind`** 判定（`browse_public`／`browse_public_more`／`find_people`），**不用關鍵字寫死**。  
> `browse_public` → 摘要＋**3** 張樣例＋追問建議；`browse_public_more` → 再展開最多 12。  
> 無 LLM 時 fallback **不當 browse**（避免誤觸）。

## 追問

同一 `session_id`：檢索用 `先前問句 + 當前追問` 組合成有效查詢；DB 只存當前 `query_text`。

## 不做
IM、跨用戶分享對話、無限長上下文摘要。
