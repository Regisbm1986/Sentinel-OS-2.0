# products/sentinel-os/

Plataforma / sistema operacional de IA (agentes, orquestração, módulos de automação e segurança). Migração planejada para a Fase 6.

**Status:** vazio — o conteúdo real hoje vive em `sentinel_os/platform/` (núcleo + módulos de pentest: nikto, spiderfoot, beef, kubehunter, john, setoolkit, dagda, kubehunter) e em `products/sentinel_os/frontend/streamlit/` (interface), ambos no `sentinel-os`/`homolog`. A Fase 6 exige primeiro separar o que é "núcleo genérico" (vai para `sentinel_platform/`) do que é "específico deste produto" (fica aqui).

Subpastas esperadas: `agents/`, `orchestrator/`, `modules/`, `security/`, `automation/`, `telemetry/`.
