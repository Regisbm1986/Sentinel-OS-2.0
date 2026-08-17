# sentinel_platform/

Núcleo de plataforma compartilhado entre todos os produtos (Career, OS, futuros). Migração planejada para a Fase 4.

**Status:** vazio — o conteúdo real hoje vive espalhado em `sentinel_os/platform/backend/{agents,api,core,database,telemetry,dashboard}` no repositório `sentinel-os`/`homolog`, que é o que o `Procfile` efetivamente executa. Subpastas esperadas: `auth/`, `agents/`, `services/`, `AI Gateway/`, `billing/`, `storage/`, `telemetry/`, `notifications/`, `analytics/`.

`storage/`, `notifications/` e `analytics/` não existem em nenhum repositório hoje — serão criados como esqueleto na Fase 7, sem código funcional (fora do escopo de uma migração estrutural).
