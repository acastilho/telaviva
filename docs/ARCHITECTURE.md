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

`apps/api/app` começa compacto e cresce por módulos de domínio (`identity`, `creators`,
`scheduling`, `chat`, `support`, `moderation`), cada um separando rotas, modelos, contratos e
persistência. Categorias são um catálogo estável com identificadores determinísticos; perfis
referenciam esse catálogo por uma relação muitos-para-muitos. O módulo `scheduling` mantém aulas,
seguidores, lembretes e notificações juntos enquanto essas regras compartilham a mesma transação.
`apps/web/src` deve evoluir por funcionalidades, mantendo componentes genéricos apenas quando
houver reutilização real.

## Agenda e notificações

Transmissões agendadas e relações de seguidores ficam no PostgreSQL. A agenda pessoal é uma
projeção das aulas futuras dos criadores seguidos mais aulas com lembrete explícito, sem duplicar
dados. A criação de uma aula gera notificações in-app para seguidores na mesma transação.

Lembretes formam uma fila durável (`stream_reminders`): ao consultar a caixa, itens vencidos são
materializados atomicamente em `notifications` e marcados como entregues, garantindo idempotência.
Esse primeiro consumidor é in-app; e-mail e push devem ser consumidores assíncronos adicionais da
mesma intenção persistida. Quando esses canais forem habilitados, um worker com retentativas e
dead-letter queue substituirá a materialização sob demanda, sem alterar os endpoints de domínio.

## Interação ao vivo

O módulo `interaction` autentica o primeiro frame do WebSocket com o access token e revalida o
papel atual no banco. Configuração, mensagens, perguntas, reações, moderação e denúncias ficam no
PostgreSQL para histórico e auditoria. Presença, fan-out e rate limit são efêmeros. O hub atual
atende uma única instância; ao escalar horizontalmente, sua interface deve receber um adaptador
Redis Pub/Sub e contadores com expiração. A mídia continua fora desse canal.

## Comércio e acesso

`commerce` separa catálogo, pedidos, pagamentos, entitlements e auditoria de acesso. Pedidos
preservam o valor e a moeda vistos pelo comprador. A fronteira de integração recebe eventos
normalizados de adaptadores autenticados, e a idempotência usa `(provider, provider_reference)`;
assim, nenhum objeto de domínio conhece payloads ou SDKs de gateways. Entitlements avulsos têm
escopo de aula e assinaturas têm escopo de criador e validade. Convites são independentes de
pagamentos. Toda entrada REST ou WebSocket consulta a mesma política no PostgreSQL e registra a
decisão, inclusive negativas.

## Gravações

O módulo `recordings` vincula uma gravação única a cada transmissão. O mesmo comando que inicia
a transmissão cria a captura em `RECORDING`; o encerramento move a intenção durável para
`PROCESSING`. Um adaptador de mídia captura/transcodifica fora da API, gera thumbnail e publica um
evento normalizado que move o arquivo para `READY`, preservando duração, metadados técnicos e
falhas. A fronteira `RecordingStorage` fornece upload e download temporários e é implementada com
a API S3, incluindo endpoints MinIO. Objetos permanecem privados: a API só assina URLs depois de
consultar `CommerceRepository.check_access`, mantendo acesso ao replay igual ao acesso à live.
A biblioteca projeta gravações prontas, entitlements ativos, convites e progresso sem duplicar
permissões. O progresso é idempotente por usuário/gravação, e cada leitura ou escrita de replay
revalida o acesso após expiração ou revogação.

## PIX e livro-razão

O módulo `finance` depende do contrato `PaymentProvider`, não de payloads ou SDKs específicos.
O adaptador fake existe apenas para desenvolvimento; adaptadores reais devem verificar a
assinatura antes de produzir um evento normalizado. Eventos ficam deduplicados por
`(provider, event_id)` e a mudança de estado, o crédito, a comissão e o entitlement da aula
ocorrem na mesma transação PostgreSQL. O saldo é uma projeção do ledger imutável, e o pedido de
saque reserva fundos atomicamente. Destinos de saque são tokens opacos emitidos externamente;
chaves PIX, agência e conta não pertencem ao modelo nem aos logs da aplicação.

## Trilhas de aprendizagem

O domínio `learning_paths` organiza gravações existentes em uma hierarquia ordenada de trilha,
módulos e aulas. A publicação exige ao menos uma aula e separa rascunhos do catálogo público.
O progresso pertence ao par usuário/aula e o percentual da trilha é calculado na leitura, sem
armazenar uma projeção que possa divergir quando o criador reorganiza o conteúdo.

## Configuração

Configuração segue variáveis de ambiente e princípios 12-factor. `.env.example` documenta nomes e valores locais não sensíveis; `.env` é ignorado. Produção deve injetar segredos pelo ambiente da plataforma. O backend valida a configuração com Pydantic Settings, enquanto valores `VITE_*` são incorporados no build do frontend.

## Saúde

- `GET /health/live`: confirma que o processo responde, sem dependências externas.
- `GET /health/ready`: confirma acesso ao PostgreSQL e Redis; retorna 503 se uma dependência falhar.
- cada serviço do Compose tem health check, e dependências aguardam prontidão.

## Segurança e papéis

O modelo inicial de controle de acesso é RBAC com `admin`, `creator` e `viewer`. Toda autorização ocorre na API; ocultar controles no frontend não é controle de segurança. Pagamentos devem usar provedor compatível com o mercado brasileiro, callbacks assinados, idempotência e livro-razão auditável. Dados sensíveis não devem aparecer em logs.

A identidade usa senhas Argon2, access tokens JWT curtos e refresh tokens rotativos, persistidos
somente como SHA-256 para permitir revogação. Logout e troca de senha revogam refresh tokens.
O cadastro público atribui `VIEWER`; a API confere o papel atual no banco em toda requisição
protegida, portanto mudanças de papel invalidam imediatamente permissões de access tokens antigos.

## Evolução e decisões pendentes

Antes do MVP serão registrados ADRs para autenticação, fornecedor/protocolo de vídeo, pagamentos, chat e estratégia de deploy. Migrações de banco serão versionadas. Filas persistentes devem ser introduzidas quando tarefas assíncronas exigirem garantia de entrega; Redis Pub/Sub sozinho não oferece essa garantia.

<!-- COMPROMISSO-GERAL-A-CASTILHO -->

---

## Compromisso Geral

**Sempre na melhor prática. No caminho do bem maior.**

**Ir até o fim sem sair do caminho, seja ele qual for.**

