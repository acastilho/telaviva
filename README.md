# Tela Viva

**Veja. Aprenda. Apoie.**

Plataforma para profissionais transmitirem seu trabalho ao vivo, compartilharem conhecimento
e receberem apoio financeiro da comunidade.

## Fundação do produto

- frontend React + TypeScript;
- API FastAPI;
- PostgreSQL e Redis;
- Docker Compose com health checks;
- documentação de produto, arquitetura e roadmap;
- CI para backend, frontend e configuração Docker.

## Executar com Docker

```bash
cp .env.example .env
docker compose up --build
```

- Aplicação: http://localhost:3000
- API: http://localhost:8000
- Documentação da API: http://localhost:8000/docs

## Desenvolvimento sem Docker

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Consulte `docs/` para decisões, limites do MVP e próximos incrementos.
