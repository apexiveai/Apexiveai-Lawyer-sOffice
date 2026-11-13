# Trademark Conflict frontend

## Local development

Copy `.env.example` to `.env` before changing frontend environment settings.
Vite loads `.env` and `.env.local` automatically. The defaults proxy API
requests to `http://127.0.0.1:8081` and leave OIDC sign-in disabled until an
authority and client ID are configured.

Run the frontend from this directory:

```powershell
npm run dev
```

For production, configure `VITE_OIDC_AUTHORITY` and `VITE_OIDC_CLIENT_ID` at
build time. Set `VITE_API_BASE_URL` to the public API origin unless the
frontend host proxies `/api`, `/evidence`, and `/health` to the backend.

## Checks

```powershell
npm run build
npm run lint
```
