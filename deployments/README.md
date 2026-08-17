# deployments/

Referência centralizada de topologia de deploy (`azure/`, `production/`, `staging/`).

**Status:** vazio — hoje a configuração de deploy real está espalhada: `ecosystem.config.js` e `Procfile` (homolog/sentinel-os) e dois workflows Azure Static Web Apps em `sentinel-os/.github/workflows/*.yml`. Esses arquivos de deploy REAIS continuam vivendo em `.github/workflows/` e na raiz de cada projeto — nunca movê-los para cá; esta pasta é só para documentação de topologia (Fase 7).
