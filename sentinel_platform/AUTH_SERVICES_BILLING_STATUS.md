# Status: auth/, services/, AI Gateway/, billing/, storage/, notifications/, analytics/

Nenhuma dessas subpastas existe hoje dentro de `sentinel_platform/`. A implementação real de autenticação, serviços de OAuth, billing e integração com IA vive dentro do produto Career (`products/sentinel-career/app/backend/{auth,app/services,payments,gpt}`) — ainda não foi extraída como algo genuinamente compartilhado entre produtos.

Extrair uma versão genérica/reutilizável dessas funcionalidades é trabalho de desenvolvimento de produto (decidir o contrato de uma API compartilhada, não só mover arquivos), fora do escopo desta migração estrutural. Esta pasta não cria os subdiretórios vazios para não sugerir que algo já foi decidido sobre esse contrato — quando o trabalho de extração acontecer, ele deve começar por aqui.

`storage/`, `notifications/` e `analytics/` não têm nenhuma implementação hoje em nenhum repositório, nem específica de produto.
