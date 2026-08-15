# Arquitetura

## Contexto

O monorepo mantém frontend, API e documentação juntos para compartilhar evolução e revisão, preservando deploys independentes. A primeira versão usa um monólito modular no backend; extrair serviços antes de haver carga real aumentaria o custo operacional sem benefício comprovado.

## Componentes

```text
Navegador ──HTTPS──> React/Vite ──REST──> FastAPI
                                      ├──> PostgreSQL (dados duráveis)
                                      └──> Redis (cache, presença e eventos efêmeros)

Navegador ──WebRTC/HLS──> Provedor de vídeo (fase de streaming)
Navegador <──WebSocket──> Canal de chat (fase de streaming)
```

- **React + TypeScript:** interface e experiência da sala ao vivo.
- **FastAPI:** regras de negócio, autenticação/autorização e integrações.
- **PostgreSQL:** fonte de verdade de usuários, transmissões, relações e transações.
- **Redis:** cache, rate limiting, presença e coordenação de tempo real; nunca é fonte única de dados financeiros.
- **Provedor de vídeo:** será escolhido por spike técnico; o tráfego de mídia não deve atravessar a API principal.

## Organização

`apps/api/app` começa compacto e deve crescer por módulos de domínio (`identity`, `streams`, `chat`, `support`, `moderation`), cada um separando rotas, casos de uso e persistência. `apps/web/src` deve evoluir por funcionalidades, mantendo componentes genéricos apenas quando houver reutilização real.

## Configuração

Configuração segue variáveis de ambiente e princípios 12-factor. `.env.example` documenta nomes e valores locais não sensíveis; `.env` é ignorado. Produção deve injetar segredos pelo ambiente da plataforma. O backend valida a configuração com Pydantic Settings, enquanto valores `VITE_*` são incorporados no build do frontend.

## Saúde

- `GET /health/live`: confirma que o processo responde, sem dependências externas.
- `GET /health/ready`: confirma acesso ao PostgreSQL e Redis; retorna 503 se uma dependência falhar.
- cada serviço do Compose tem health check, e dependências aguardam prontidão.

## Segurança e papéis

O modelo inicial de controle de acesso é RBAC com `admin`, `creator` e `viewer`. Toda autorização ocorre na API; ocultar controles no frontend não é controle de segurança. Pagamentos devem usar provedor compatível com o mercado brasileiro, callbacks assinados, idempotência e livro-razão auditável. Dados sensíveis não devem aparecer em logs.

## Evolução e decisões pendentes

Antes do MVP serão registrados ADRs para autenticação, fornecedor/protocolo de vídeo, pagamentos, chat e estratégia de deploy. Migrações de banco serão versionadas. Filas persistentes devem ser introduzidas quando tarefas assíncronas exigirem garantia de entrega; Redis Pub/Sub sozinho não oferece essa garantia.
