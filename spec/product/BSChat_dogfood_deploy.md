# BSChat Dogfood 部署清單 — 給同事用的測試站

> **現行鎖定方案（2026-07-17）**  
> **Netlify（前端）+ Railway（API）+ Neon（Postgres + Object Storage）+ Upstash（Redis）+ Resend（信）**  
>
> 目標：同事用瀏覽器打開 **HTTPS** 網址，註冊／登入後可掃卡、搜尋；企業租戶由 ops provision 開通後邀請成員。  
> 預計 **半天～一天**（含帳號申請）。  
> 權威 env 範本：`backend/.env.dogfood.example`、`frontend/.env.dogfood.example`。  
> 建置設定：repo 根目錄 `netlify.toml`（`base = "frontend"`）。

---

## 架構（現行）

```
瀏覽器 ──HTTPS──► Netlify (Next.js PWA · @netlify/next)
                      │ NEXT_PUBLIC_API_URL
                      ▼
                 Railway (FastAPI Dockerfile)
                      ├── Neon Postgres (+ pgvector / pg_trgm)
                      ├── Neon Object Storage (名片圖 · public_read)
                      ├── Upstash Redis
                      └── Resend (邀請／重設密碼)
```

| 元件 | 平台 | 為什麼 |
|------|------|--------|
| 前端 | **Netlify** | Next.js + HTTPS（相機／PWA）；runtime 自動處理 SSR |
| 後端 API | **Railway** | 常駐容器；OCR／搜尋不適合前端 Serverless |
| 資料庫 | **Neon** | `pgvector`／`pg_trgm` |
| 名片圖檔 | **Neon Object Storage**（S3 · Beta） | 與 Neon 同帳；bucket=`public_read` |
| Redis | **Upstash** | 啟動要連；先 `USE_CELERY_WORKERS=false` |
| 郵件 | **Resend** | 企業邀請、忘記密碼 |

**明確不做（此輪）**：後端上 Netlify Functions；圖檔塞 DB base64；Zeabur／Linode 單機（可當備案）。

本機已備好：
- `backend/Dockerfile`
- `backend/.env.dogfood.example`
- `frontend/.env.dogfood.example`
- `netlify.toml`

---

## 步驟 0 — 你要先有的帳號

1. GitHub（程式已推上去，或先 push 一個 branch）
2. [Netlify](https://app.netlify.com)
3. [Railway](https://railway.app)
4. [Neon](https://neon.tech)
5. [Upstash](https://upstash.com)
6. Neon Object Storage（同專案建 `public_read` bucket）— 見步驟 3
7. Gemini API Key（你本機 `.env` 已有可沿用）
8. Resend（邀請信／重設密碼）

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

## 步驟 3 — Neon Object Storage（名片圖）

> Beta；目前文件標註區域偏 **AWS us-east-2**。見 [Neon Object Storage](https://neon.com/docs/storage/overview)。

1. Neon Console → 選 branch → **Storage** → New bucket  
   - 名稱例如 `bschat-cards`  
   - Access：**`public_read`**（瀏覽器才能直接 `<img src>`）
2. 同 branch → **Credentials** → Create  
   - scopes：`storage:read` + `storage:write`  
   - 下載／複製 `.env` 片段（只顯示一次）
3. 填到 Railway：

```text
STORAGE_BACKEND=neon
AWS_ENDPOINT_URL_S3=https://br-....storage....aws.neon.build
AWS_ACCESS_KEY_ID=nak_live_...
AWS_SECRET_ACCESS_KEY=nsk_live_...
AWS_REGION=us-east-2
S3_BUCKET_NAME=bschat-cards
STORAGE_PUBLIC_BASE_URL=https://br-....storage....aws.neon.tech/bschat-cards
```

`STORAGE_PUBLIC_BASE_URL` = 公開讀取 origin（含 bucket 名、**無**結尾 `/`）。  
物件 key 為 `uploads/{user_id}/{card_id}.jpg`，與 DB 的 `/uploads/...` 對齊。

（若堅持用 Cloudflare R2：設 `STORAGE_BACKEND=r2` + `R2_*`，見舊版範例。）

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
   - Neon Object Storage（`STORAGE_BACKEND=neon`、`AWS_*`、`S3_BUCKET_NAME`、`STORAGE_PUBLIC_BASE_URL`）
   - `CORS_ORIGINS` 先暫填，等 Netlify 網址出來再改成精確前端網址
4. 產生 Public Domain，例如 `https://bschat-api-xxx.up.railway.app`
5. 設：

```text
API_BASE_URL=https://bschat-api-xxx.up.railway.app
FRONTEND_BASE_URL=https://YOUR-SITE.netlify.app
```

6. 部署後在 Railway 跑 migration：`alembic upgrade head`（或 release command）
7. 打開 `https://你的API/health` 應回 `{"status":"ok"}`  
8. 打開 `/docs` 可試註冊／登入（dogfood 請 `ALLOW_DEV_LOGIN=false`）

---

## 步驟 5 — Netlify 前端

1. [Netlify](https://app.netlify.com) → Add new site → Import from Git → 選本 repo  
2. Build settings（`netlify.toml` 已寫好，通常不用手填）：
   - **Base directory** = `frontend`（或留空讓 toml `base` 生效）
   - **Build command** = `npm run build`
   - **Publish directory** = `.next`
3. Environment Variables：

```text
NEXT_PUBLIC_API_URL=https://bschat-api-xxx.up.railway.app
```

（可選）`NEXT_PUBLIC_MEDIA_BASE_URL` — 若前端要覆寫媒體 CDN。

4. Deploy → 得到 `https://xxx.netlify.app`（或自訂網域）
5. 回到 Railway，把 CORS／前端 base 改成：

```text
CORS_ORIGINS=https://xxx.netlify.app
FRONTEND_BASE_URL=https://xxx.netlify.app
```

（可再加 `http://localhost:3000` 方便本機對測）

6. 重新部署後端（讓 CORS 生效）

**CLI 備援**（本機已登入時）：

```bash
npx netlify login
npx netlify link   # 選／建 site
npx netlify env:set NEXT_PUBLIC_API_URL "https://bschat-api-xxx.up.railway.app"
npx netlify deploy --build --prod
```

---

## 步驟 6 — 給同事的使用說明（直接轉傳）

```text
1. 開 https://xxx.netlify.app/login
2. 方案選 Pro（或 Free 也行）
3. Email 填自己的（每人不同）
4. 顯示名稱填真名
5. 公司代號大家填一樣：例如 acme-team
6. 註冊／登入
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
| CORS error | `CORS_ORIGINS` 必須完全等於 Netlify 網址（含 https、無尾斜線） |
| 搜尋／OCR 假資料 | 確認 `GEMINI_API_KEY`、`OCR_USE_MOCK=false` |
| 圖片破圖 | `STORAGE_PUBLIC_BASE_URL` 是否含 bucket、bucket 是否 `public_read` |
| DB extension 錯誤 | Neon 執行 `vector` + `pg_trgm` |
| 部署後名片圖不見 | 未設 Neon Storage／仍用 ephemeral 本機碟 |
| Netlify build 失敗 | 確認 `base=frontend`、Node 20、`NEXT_PUBLIC_API_URL` 已設 |

---

## 暫用本機磁碟（不建議，僅極短測）

若還沒開 Neon Object Storage：

```text
STORAGE_BACKEND=local
```

並在 Railway 加 Volume 掛到 `/app/storage/uploads`。  
重部署仍可能丟檔 → **正式 dogfood 請用 Neon Object Storage（或 R2）**。

---

## 你跟 AI 協作時怎麼喊我

準備好帳號後，把這三個網址貼回來即可繼續排查：

1. Netlify 前端 URL  
2. Railway API URL（`/health` 截圖或回應）  
3. Neon Storage bucket 是否已設 `public_read`  

我可以依實際錯誤幫你改 CORS／env／建置設定。
