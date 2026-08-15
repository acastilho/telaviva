# TelaViva

**Veja. Aprenda. Apoie.**

TelaViva é uma plataforma de transmissões ao vivo na qual profissionais compartilham seu trabalho para que espectadores aprendam, interajam e apoiem seus criadores.

## Estrutura

```text
apps/
  api/       API FastAPI
  web/       aplicação React + TypeScript
docs/        produto, arquitetura e roadmap
compose.yaml ambiente local completo
```

## Pré-requisitos

- Docker 24+ com Docker Compose; ou
- Node.js 22+, Python 3.12+, PostgreSQL 16 e Redis 7 para execução sem Docker.

## Início rápido

1. Copie a configuração de exemplo: `cp .env.example .env`.
2. Inicie os serviços: `docker compose up --build`.
3. Acesse o frontend em <http://localhost:5173> e a documentação da API em <http://localhost:8000/docs>.

O Compose aguarda os health checks do PostgreSQL, Redis e API antes de liberar seus dependentes. A configuração de exemplo é exclusiva para desenvolvimento local e não deve ser reutilizada em produção.

## Desenvolvimento local

### API

```bash
cd apps/api
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

Antes de iniciar a API pela primeira vez, aplique as migrações ao PostgreSQL, em ordem:

```bash
for migration in migrations/*.sql; do
  psql "${DATABASE_URL/postgresql+asyncpg/postgresql}" -f "$migration"
done
```

No ambiente Docker Compose essa migração é aplicada automaticamente pelo serviço `migrate`.

Configure `JWT_SECRET` com pelo menos 32 caracteres (obrigatório e sem valor padrão em produção).
Configure uma lista explícita em `API_CORS_ORIGINS`; curingas são recusados porque a API aceita
credenciais. A API aplica headers defensivos, limite de corpo (1 MiB), rate limiting por cliente
(120 requisições/minuto e 20/minuto nos fluxos sensíveis de autenticação) e logs JSON sem corpo,
query string, cookies ou tokens. Em múltiplas réplicas, replique esses limites no proxy/edge para
uma janela compartilhada. `X-Request-ID` pode ser enviado com até 64 caracteres alfanuméricos e é
sempre devolvido para correlação; respostas não devem ser armazenadas em cache.
Os endpoints de autenticação estão sob `/auth`: cadastro, login, refresh, logout,
recuperação/reset de senha e consulta do usuário atual. O cadastro público sempre cria `VIEWER`;
promoções para `CREATOR` ou `ADMIN` devem ocorrer por um fluxo administrativo confiável.

Os endpoints públicos `GET /categories` e `GET /creators/{user_id}` expõem o catálogo inicial
e os perfis profissionais. Criadores autenticados configuram o próprio perfil com
`PUT /creators/me`; verificação e papel não podem ser alterados por esse endpoint.

Criadores com perfil publicado agendam aulas em `POST /streams`; a agenda pública pode ser
consultada em `GET /streams`. Usuários autenticados seguem criadores com
`PUT /creators/{id}/follow`, consultam sua seleção em `GET /agenda/me` e configuram um lembrete
idempotente em `PUT /streams/{id}/reminder`. A caixa in-app fica em `GET /notifications`, com
filtro `unread_only`, e confirma leitura em `PATCH /notifications/{id}/read`.

Datas da API usam ISO 8601 com fuso horário. Níveis aceitos são `BEGINNER`, `INTERMEDIATE`,
`ADVANCED` e `ALL_LEVELS`; acessos são `FREE`, `PAID`, `SUBSCRIBERS` ou `PRIVATE`. Lembretes são
persistentes e materializados uma única vez na caixa in-app;
o modelo mantém o agendamento separado da entrega para receber adaptadores de e-mail e push.

Criadores cadastram produtos avulsos ou assinaturas em `POST /products`; espectadores congelam
preço e moeda em um pedido com `POST /orders`. Adaptadores de gateway validam a assinatura do
callback e enviam o evento normalizado ao endpoint administrativo `POST /payment-events`, sem
acoplar o domínio ao formato de um provedor. Um pagamento aprovado cria o entitlement e um
reembolso o revoga. Antes de entregar a sala, `POST /streams/{id}/access` verifica e audita o
acesso; o WebSocket repete obrigatoriamente essa validação. Aulas privadas usam convites criados
em `PUT /streams/{id}/invites/{user_id}`.

Gorjetas e compras avulsas são cobradas por PIX em `POST /pix/charges`. O adaptador `fake`,
disponível somente fora de produção, exige `x-fake-signature: development-webhook` no callback
`POST /pix/webhooks/fake`. Configure `PAYMENT_PROVIDER` para um adaptador real em produção e
`PLATFORM_FEE_RATE` para a comissão (padrão local: `0.10`). O webhook é idempotente por provedor
e ID de evento e alimenta um livro-razão auditável. Criadores consultam `/finance/balance` e
`/finance/history` e solicitam saques em `/finance/withdrawals`. O saque aceita somente uma
referência opaca `dest_*` previamente tokenizada pelo provedor; chave PIX e dados bancários não
são recebidos nem persistidos pela TelaViva.

Cada transmissão possui configuração pública em `GET /streams/{id}/interaction-settings`; o
criador ou um administrador altera chat, perguntas e reações com `PUT` no mesmo caminho. O canal
`WS /streams/{id}/live` exige como primeira mensagem
`{"type":"authenticate","token":"<access token>"}`. Depois de `ready`, clientes enviam
`message`, `question` ou `reaction` e recebem eventos, configuração e `viewer_count`. O histórico
autenticado está em `GET /streams/{id}/events`.

Criador e administradores aplicam `mute` ou `ban` em `POST /streams/{id}/moderation`; espectadores
denunciam eventos em `POST /streams/{id}/reports`. O servidor limita cada usuário a oito
interações por janela de dez segundos. Ban encerra conexões ativas e mute impede novas interações.

O ciclo da transmissão usa `POST /streams/{id}/broadcast/start` e
`POST /streams/{id}/broadcast/end`; iniciar e encerrar a live inicia e encerra a gravação
automaticamente. O arquivo passa por `RECORDING`, `PROCESSING` e `READY` (ou `FAILED`). Um worker
de mídia recebe a URL privada de upload, transcodifica, gera thumbnail e informa duração e
metadados pelos callbacks administrativos normalizados. `GET /streams/{id}/recording` entrega
URLs temporárias de reprodução e thumbnail somente após aplicar a mesma política comercial da
transmissão. O storage usa o contrato S3 e aceita AWS S3 ou MinIO por `RECORDING_S3_ENDPOINT_URL`;
bucket, região e validade das URLs usam `RECORDING_BUCKET`, `RECORDING_S3_REGION` e
`RECORDING_URL_TTL_SECONDS`.

`GET /recordings/library` reúne gravações prontas e autorizadas em minhas aulas, retomada,
compras, assinaturas e histórico. `GET /recordings/{id}` entrega o replay após nova validação de
acesso e `PUT /recordings/{id}/progress` salva a posição, limita-a à duração e conclui a aula a
partir de 95%. A migração `008_recording_library.sql` persiste o progresso.

Criadores montam cursos em `POST /learning-paths`, acrescentam módulos e gravações como aulas,
definem a ordem explicitamente e publicam em `PUT /learning-paths/{id}/publish`. O catálogo
público está em `GET /learning-paths`; rascunhos são visíveis apenas ao autor ou administrador.
Cada trilha possui descrição, nível e preço opcional. O progresso por aula é idempotente em
`PUT /learning-paths/lessons/{id}/progress` e a resposta agrega o percentual da trilha.

O envio do link de recuperação é um adaptador deliberadamente vazio nesta fase. Para produção,
substitua `get_recovery_notifier` por uma integração de e-mail; tokens nunca são persistidos em claro.

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

O dashboard do espectador reúne transmissões ao vivo, aulas agendadas, categorias e
criadores. A busca e os filtros de descoberta são aplicados no cliente ao catálogo atual;
entrar em uma transmissão exige autenticação. Enquanto os endpoints de transmissões não
forem implementados, o frontend usa dados demonstrativos tipados para essa experiência.
A opção **Painel do criador** abre uma visão operacional responsiva com agenda, gravações,
alunos, seguidores, receita, gorjetas, vendas, analytics, histórico financeiro e configuração
de preços. O CTA de transmissão leva ao estúdio existente; métricas e preços permanecem
demonstrativos no cliente até a integração do frontend autenticado com a API.
A opção **Administração** abre o painel operacional responsivo com usuários, criadores,
transmissões, gravações, pagamentos, denúncias, categorias, comissões, auditoria, métricas,
bloqueios e fila de moderação. Os dados e as ações são demonstrativos no cliente até a
integração do frontend com uma sessão autenticada de papel `ADMIN` e endpoints administrativos.
A navegação inclui a biblioteca demonstrativa com filtros por compra/assinatura, histórico,
retomada e página de replay; a integração HTTP substituirá os dados tipados quando o fluxo de
autenticação do frontend estiver conectado à API.

O botão **Criar live** abre o estúdio do criador. Monitor, janela ou aba são escolhidos no
seletor nativo do navegador (`getDisplayMedia`), sempre mediante autorização explícita; câmera
e microfone usam `getUserMedia`. O estúdio oferece preview, layouts, pausa, troca de fonte,
silenciamento e encerramento local. A distribuição para espectadores depende do provedor de
vídeo ainda previsto no roadmap e não é simulada pelo frontend.
Quando suportado pelo navegador, o seletor prefere uma aba, exclui a própria aba do TelaViva e
permite trocar a fonte sem conceder acesso permanente. Áudio da tela não é capturado. Encerrar,
fechar o estúdio ou desmontar a tela interrompe todas as trilhas de mídia.
O estúdio permite habilitar ou desabilitar chat, perguntas e reações antes da transmissão.

## Qualidade

```bash
make test       # testes de API e frontend
make lint       # Ruff e ESLint
make typecheck  # mypy e TypeScript
```

O cenário E2E da API (`apps/api/tests/test_e2e.py`) percorre cadastro, login, perfil do
criador, agenda e descoberta, compra, entrada na transmissão via WebSocket, gorjeta,
encerramento, processamento, replay e operação administrativa. PostgreSQL, storage e o
processador de mídia são substituídos por adaptadores em memória; os contratos HTTP,
autorização, JWT e ciclo entre domínios permanecem reais.

As decisões de produto e engenharia estão em [docs/PRD.md](docs/PRD.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) e [docs/ROADMAP.md](docs/ROADMAP.md).
