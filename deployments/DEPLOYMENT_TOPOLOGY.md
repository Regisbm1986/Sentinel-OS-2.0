# Topologia de deploy real

**Atualizado na Fase 8 (cutover em andamento):**

- **pm2** (`sentinel-career-api`): processo real de produção, cutover feito — agora roda a partir de `/home/sentineladmin/sentinel-ai-monorepo/products/sentinel-career/app` (`backend.app.main:app`), configurado em `ecosystem.config.js` no `homolog` (`.venv` reaproveitado de lá). Validado ao vivo.
- **Procfile** (`sentinel-os`/`homolog`, ainda não migrado): `web: gunicorn -k uvicorn.workers.UvicornWorker sentinel_os.platform.backend.api.main:app` — usado pelo processo da plataforma Sentinel OS (`products/sentinel-os/` no monorepo ainda não tem um Procfile próprio nem está em produção).
- **Azure Static Web Apps** (2 workflows, trazidos para `.github/workflows/` no monorepo, caminhos já corrigidos, **gatilho ainda restrito a `main`** — não disparam em push para `monorepo-migration`):
  - `azure-static-web-apps-agreeable-desert-05321e310.yml` → `app_location: products/sentinel-career/landing` (site institucional estático)
  - `azure-static-web-apps-black-meadow-0b37a7810.yml` → `app_location: products/sentinel-career/app/frontend` (SPA Vite/React), `output_location: dist`

Repositório GitHub: monorepo pushado como branch `monorepo-migration` em `Regisbm1986/Sentinel-AI-Holding` (não `main` ainda — promoção é uma decisão separada).

`azure/`, `production/`, `staging/` como subpastas dedicadas ainda não existem — não há conteúdo de infraestrutura real para colocar nelas (ver `infrastructure/README.md`).
