# toolloop-agent

🇪🇸 Versão em espanhol: [README.es.md](README.es.md)

Agente autônomo com function calling que encadeia busca na web, consultas ao
banco de dados e envio de e-mails (simulado), mostrando passo a passo seu ciclo
de pensamento → ação → observação. Stack: FastAPI · React · LLM com tool
calling (Anthropic).

📄 **Documentação completa:**
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitetura, stack, modelo
  de dados e por que SQLite/SQLAlchemy foi escolhido em vez do Supabase.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — o que está implementado (Sprints 0 a 5)
  e o status da Sprint 6 (repositório pronto para deploy).
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — decisões de design pontuais.
- [`docs/DEPLOY.md`](docs/DEPLOY.md) — guia passo a passo para fazer o deploy
  (Fly.io + Vercel, alternativas, migração para Postgres se necessário).
- [`docs/BLOG_POST.md`](docs/BLOG_POST.md) — rascunho do post sobre o
  padrão ReAct e as decisões de design do projeto.

## Status atual: Sprints 0 a 5

O que já funciona: o agente consegue encadear três ferramentas via tool
calling nativo do LLM, e é possível acompanhar seu trace (ação → observação →
resposta final) em tempo real, com tratamento robusto de erros (uma tool que
falha não derruba a requisição, e um limite de iterações evita loops infinitos):

- `buscar_eventos`: consulta a agenda interna (parâmetros tipados, sem SQL
  livre).
- `buscar_web`: busca na web mockada por padrão (ex.: clima), ou real se
  `TAVILY_API_KEY` estiver configurada.
- `enviar_email`: "envia" um e-mail inserindo uma linha em `sent_emails` (sem
  SMTP real), somente quando o usuário pede isso explicitamente.

Dois endpoints de chat: `POST /api/chat` (resposta final de uma só vez) e
`POST /api/chat/stream` (SSE, transmite cada passo à medida que acontece — é o
que o frontend usa). `GET /api/conversations/{id}/steps` retorna o trace
persistido de uma conversa.

Para testar com dados de exemplo:

```bash
cd backend && python -m scripts.seed_events
```

Em seguida, pergunte ao agente algo como *"veja a previsão do tempo para
amanhã e, se tivermos um evento ao ar livre nesse dia, avise a equipe por
e-mail"*.

## Como executar

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # e preencher ANTHROPIC_API_KEY
uvicorn app.main:app --reload
```

Roda em `http://localhost:8000`. Documentação interativa em `/docs`.

Testes:

```bash
pytest
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Roda em `http://localhost:5173`.

### Com Docker

```bash
export ANTHROPIC_API_KEY=sk-ant-...
docker compose up --build
```

### Deploy

Veja [`docs/DEPLOY.md`](docs/DEPLOY.md) para o passo a passo (backend no
Fly.io, frontend na Vercel e como conectá-los).

## Estrutura

```
backend/    # FastAPI + SQLAlchemy (SQLite) + cliente Anthropic
frontend/   # React + Vite + TypeScript
docs/       # Arquitetura, roadmap e decisões de design
```
