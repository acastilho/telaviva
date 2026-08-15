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

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

## Qualidade

```bash
make test       # testes de API e frontend
make lint       # Ruff e ESLint
make typecheck  # mypy e TypeScript
```

As decisões de produto e engenharia estão em [docs/PRD.md](docs/PRD.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) e [docs/ROADMAP.md](docs/ROADMAP.md).
