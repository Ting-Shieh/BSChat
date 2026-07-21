# BSChat Frontend

Next.js 15 PWA + features/shared 架構。

## Quick start

```bash
cp .env.local.example .env.local
npm install
npm run dev
```

開啟 http://localhost:3000/login，使用 Dev 登入（需 backend 在 :8001 運行）。

## 目錄

| 路徑 | 用途 |
|------|------|
| `app/` | 薄路由層 |
| `features/` | 按模組划分（auth, capture, contacts, search, enrichment, actions） |
| `shared/` | 跨模組 UI、hooks、api-client |

## PWA

- Serwist service worker：`sw.ts`（勿放 `app/`，會弄壞 `/search`／`/settings` SSR）
- Manifest：`app/manifest.ts`
- 開發模式 SW 預設停用（`next.config.ts`）

## 類型同步（Phase 2）

```bash
npx openapi-typescript http://localhost:8001/openapi.json -o shared/types/openapi.d.ts
```
