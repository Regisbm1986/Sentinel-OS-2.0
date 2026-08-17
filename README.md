# Sentinel AI — Monorepo

Consolidação em andamento de 3 repositórios físicos (`sentinel-os`, `homolog/sentinel-os-hml`, `sentinel-ai`) numa árvore única, seguindo o plano de migração faseado.

**Status:** esqueleto criado (Fase 3). Nenhum código funcional foi migrado ainda — isso acontece nas Fases 4-6. Nada em produção aponta para este repositório.

Plano completo de migração: ver histórico do assistente / plano salvo em `~/.claude/plans/`.

## Estrutura

- `sentinel_platform/` — núcleo compartilhado da plataforma (auth, agents, services, billing, telemetry...)
- `products/sentinel-career/` — produto comercial de carreira
- `products/sentinel-os/` — plataforma/sistema operacional de IA
- `shared/`, `infrastructure/`, `packages/`, `frontend/`, `backend/`, `documentation/`, `deployments/`, `monitoring/`, `tools/`

Cada pasta tem seu próprio `README.md` explicando propósito e status (esqueleto vazio vs. conteúdo real migrado).
