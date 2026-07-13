# BSChat Dogfood 部署清單 — 給同事用的測試站

> 目標：同事用瀏覽器打開一個 **HTTPS 網址**，Dev 登入後就能掃卡／搜尋。  
> 不需要正式註冊系統。預計 **半天～一天**（含帳號申請）。

---

## 架構（最省事組合）

| 元件 | 平台 | 為什麼 |
|------|------|--------|
| 前端 | **Vercel** | Next.js + HTTPS（相機需要） |
| 後端 API | **Railway** | 常駐容器、好接 Dockerfile |
| 資料庫 | **Neon** | 免費層可開 `pgvector` / `pg_trgm` |
| Redis | **Upstash** | 免費層；`USE_CELERY_WORKERS=false` 時幾乎不用，但啟動仍要能連 |
| 名片圖檔 | **Cloudflare R2**（強烈建議） | Railway 硬碟會因重部署消失 |

本機已備好：
- `backend/Dockerfile`
- `backend/.env.dogfood.example`
- `frontend/.env.dogfood.example`

---

## 步驟 0 — 你要先有的帳號

1. GitHub（程式已推上去，或先 push 一個 branch）
2. [Vercel](https://vercel.com)
3. [Railway](https://railway.app)
4. [Neon](https://neon.tech)
5. [Upstash](https://upstash.com)
6. Cloudflare（R2）— 若暫時沒有，見文末「暫用本機磁碟」
7. Gemini API Key（你本機 `.env` 已有可沿用）

---

## 步驟 1 — Neon 資料庫

1. 新建 Project → 複製 **connection string**
2. 改成 asyncpg 格式，例如：

```text
postgresql+asyncpg://user:pass@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?ssl=require
```

3. 在 Neon SQL Editor 執行：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

---

## 步驟 2 — Upstash Redis

1. 新建 Redis → 複製 `rediss://...` URL  
2. 填到後端 `REDIS_URL`

---

## 步驟 3 — Cloudflare R2（名片圖）

1. 建 Bucket（public 讀取或綁自訂網域）
2. 建 API Token（Object Read/Write）
3. 記下：`R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET_NAME` / `R2_PUBLIC_URL`

後端設：

```text
STORAGE_BACKEND=r2
STORAGE_PUBLIC_BASE_URL=https://你的R2公開網域
R2_PUBLIC_URL=https://你的R2公開網域
```

---

## 步驟 4 — Railway 後端

1. New Project → Deploy from GitHub → **Root Directory = `backend`**
2. 用 Dockerfile 部署（repo 內已有）
3. Variables 貼上 `backend/.env.dogfood.example` 的鍵，填真實值：
   - `DATABASE_URL`（Neon）
   - `REDIS_URL`（Upstash）
   - `JWT_SECRET`（隨機長字串）
   - `GEMINI_API_KEY`
   - `USE_CELERY_WORKERS=false`
   - `DEBUG=false`
   - R2 相關
   - `CORS_ORIGINS` 先暫填 `*` 不行的話等 Vercel 網址出來再改
4. 產生 Public Domain，例如 `https://bschat-api-xxx.up.railway.app`
5. 設：

```text
API_BASE_URL=https://bschat-api-xxx.up.railway.app
```

6. 打開 `https://你的API/health` 應回 `{"status":"ok"}`  
7. 打開 `/docs` 可試 `POST /api/v1/auth/dev-login`

---

## 步驟 5 — Vercel 前端

1. Import GitHub repo → **Root Directory = `frontend`**
2. Environment Variables：

```text
NEXT_PUBLIC_API_URL=https://bschat-api-xxx.up.railway.app
```

3. Deploy → 得到 `https://xxx.vercel.app`
4. 回到 Railway，把 CORS 改成：

```text
CORS_ORIGINS=https://xxx.vercel.app
```

（可再加 `http://localhost:3000` 方便本機對測）

5. 重新部署後端（讓 CORS 生效）

---

## 步驟 6 — 給同事的使用說明（直接轉傳）

```text
1. 開 https://xxx.vercel.app/login
2. 方案選 Pro（或 Free 也行）
3. Email 填自己的（每人不同）
4. 顯示名稱填真名
5. 公司代號大家填一樣：例如 acme-team
6. 按 Dev 登入
7. 底部「＋」連拍收名片；「搜尋」用自然語言找人
```

提醒：這是 **內部測試站**，不要對外公開宣傳；JWT／Gemini key 勿貼到群組。

---

## 步驟 7 — 你怎么确认团队池有通

1. 你登入 `you@company.com` + 公司代號 `acme-team` → 掃 3 張  
2. 同事登入 `colleague@company.com` + **同一個** `acme-team`  
3. 同事開「名片庫」應看到你的卡，標「由你收錄」

---

## 常見問題

| 狀況 | 處理 |
|------|------|
| CORS error | `CORS_ORIGINS` 必須完全等於 Vercel 網址（含 https、無尾斜線） |
| 搜尋／OCR 假資料 | 確認 `GEMINI_API_KEY`、`OCR_USE_MOCK=false` |
| 圖片破圖 | R2 公開網域／`API_BASE_URL`／`STORAGE_PUBLIC_BASE_URL` |
| DB extension 錯誤 | Neon 執行 `vector` + `pg_trgm` |
| 部署後名片圖不見 | 沒用 R2、用了 ephemeral 本機磁碟 |

---

## 暫用本機磁碟（不建議，僅極短測）

若還沒開 R2：

```text
STORAGE_BACKEND=local
```

並在 Railway 加 Volume 掛到 `/app/storage/uploads`。  
重部署仍可能丟檔 → **正式 dogfood 請用 R2**。

---

## 你跟 AI 協作時怎麼喊我

準備好帳號後，把這三個網址貼回來即可繼續排查：

1. Vercel 前端 URL  
2. Railway API URL（`/health` 截圖或回應）  
3. 是否已開 R2  

我可以依實際錯誤幫你改 CORS／env／建置設定。
