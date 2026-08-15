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

Cada transmissão possui configuração pública em `GET /streams/{id}/interaction-settings`; o
criador ou um administrador altera chat, perguntas e reações com `PUT` no mesmo caminho. O canal
`WS /streams/{id}/live` exige como primeira mensagem
`{"type":"authenticate","token":"<access token>"}`. Depois de `ready`, clientes enviam
`message`, `question` ou `reaction` e recebem eventos, configuração e `viewer_count`. O histórico
autenticado está em `GET /streams/{id}/events`.

Criador e administradores aplicam `mute` ou `ban` em `POST /streams/{id}/moderation`; espectadores
denunciam eventos em `POST /streams/{id}/reports`. O servidor limita cada usuário a oito
interações por janela de dez segundos. Ban encerra conexões ativas e mute impede novas interações.

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

O botão **Criar live** abre o estúdio do criador. Monitor, janela ou aba são escolhidos no
seletor nativo do navegador (`getDisplayMedia`), sempre mediante autorização explícita; câmera
e microfone usam `getUserMedia`. O estúdio oferece preview, layouts, pausa, troca de fonte,
silenciamento e encerramento local. A distribuição para espectadores depende do provedor de
vídeo ainda previsto no roadmap e não é simulada pelo frontend.
O estúdio permite habilitar ou desabilitar chat, perguntas e reações antes da transmissão.

## Qualidade

```bash
make test       # testes de API e frontend
make lint       # Ruff e ESLint
make typecheck  # mypy e TypeScript
```

As decisões de produto e engenharia estão em [docs/PRD.md](docs/PRD.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) e [docs/ROADMAP.md](docs/ROADMAP.md).
