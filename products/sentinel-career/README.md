# products/sentinel-career/

Produto comercial de carreira (currículo, LinkedIn ATS, vagas, entrevistas). Migração planejada para a Fase 5.

**Status:** vazio — o conteúdo real hoje vive em `products/sentinel_career/` (underscore) no `homolog`/`sentinel-os` (backend FastAPI + frontend Vite/React) e em `products/sentinel-career/frontend/landing` (hífen, site estático deployado via Azure Static Web Apps). A Fase 5 decide como acomodar os dois sob um único nome sem quebrar a invocação do backend (que usa dotted-path Python, incompatível com hífen) nem os workflows Azure.

Subpastas esperadas: `resume/`, `linkedin/`, `jobs/`, `ats/`, `interview/`, `dashboard/`, `billing/`, `analytics/`. `interview/` e `resume/` (como módulo nomeado) não existem hoje em nenhum repositório.
