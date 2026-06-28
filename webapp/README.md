# Web application — Next.js

Public lead intake form and internal staff UI. Calls the API over HTTP only — no direct database or file access.

## Run locally

```powershell
cd webapp
npm install
npm run dev
```

App: http://localhost:3000

Set `NEXT_PUBLIC_API_URL` in `.env.local` (see root `.env.example`).
