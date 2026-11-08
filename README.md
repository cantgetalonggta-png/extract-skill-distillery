# EXTRACT Skill Distillery

Static console for the Google Drive **EXTRACT** folder (272 items).

## Features
- Full reconciled inventory (Drive file IDs, MIME, size, status)
- Distilled skill/doc knowledge base
- Security quarantine for secrets and binaries (never executed)
- Tabs: Skills, Docs, Inventory, Security, Product

## Run locally
```bash
python3 -m http.server 5173 --directory .
```

## Deploy
Vercel requires `VERCEL_TOKEN` (not stored here). Scope from source: `echo-ec69`.

```bash
npx vercel --scope echo-ec69 deploy --prod
```

## Safety
Drive originals unchanged. APK/RPM binaries and vault/key materials blocked from knowledge body.
