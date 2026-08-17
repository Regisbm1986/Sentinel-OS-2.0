# Status: orchestrator/, security/, automation/

Nenhuma dessas subpastas existe com este nome hoje. Funcionalidade equivalente:
- "orchestrator" → o motor de orquestração genérico vive em `sentinel_platform/backend/agents/` (orchestrator.py, task_queue.py, worker_dispatcher.py etc.), compartilhado com outros produtos, não duplicado aqui.
- "security"/"automation" → cobertos implicitamente por `backend/modules/{nikto,spiderfoot,beef,kubehunter,john,setoolkit,dagda,enum4linux}` e por `backend/platform/{module_discovery,operations_platform}`.

Renomear/reorganizar esses módulos para bater literalmente com `orchestrator/`, `security/`, `automation/` é uma decisão de nomenclatura de produto, não uma migração estrutural — não fiz isso sem confirmação.
