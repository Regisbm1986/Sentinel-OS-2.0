# Topologia de deploy real (referência, não mover os arquivos citados aqui)

- **pm2** (`sentinel-career-api`): processo real em produção-homolog, roda a partir de `/home/sentineladmin/homolog/sentinel-os-hml`, configurado em `ecosystem.config.js` na raiz daquele repositório.
- **Procfile** (`sentinel-os`/`homolog`): `web: gunicorn -k uvicorn.workers.UvicornWorker sentinel_os.platform.backend.api.main:app` — usado pelo processo da plataforma Sentinel OS.
- **Azure Static Web Apps** (2 workflows em `sentinel-os/.github/workflows/`):
  - `azure-static-web-apps-agreeable-desert-05321e310.yml` → `app_location: products/sentinel-career/frontend/landing` (site institucional estático)
  - `azure-static-web-apps-black-meadow-0b37a7810.yml` → `app_location: products/sentinel_career/frontend` (SPA Vite/React), `output_location: dist`

Nenhum desses arquivos de deploy foi movido para dentro do monorepo ainda — eles continuam vivendo nos repositórios originais até o cutover real (Fase 8), quando precisarão ser atualizados para os novos caminhos (`products/sentinel-career/landing`, `products/sentinel-career/app`) no mesmo commit que move os arquivos de código.

`azure/`, `production/`, `staging/` como subpastas dedicadas ainda não existem — não há conteúdo de infraestrutura real para colocar nelas (ver `infrastructure/README.md`).
