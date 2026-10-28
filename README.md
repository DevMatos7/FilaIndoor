# REAL Fila & Indoor

Plataforma própria de filas, atendimento presencial e vídeo indoor (MVP iniciando pelo açougue).

## Stack

- **Backend:** Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL
- **Frontend:** React, TypeScript, Vite, Tailwind
- **Infra:** Docker Compose

## Portas (exclusivas — sem conflito com Checklist/Carga)

| Serviço   | Porta |
|-----------|-------|
| Web       | **5180** |
| API       | **8010** |
| Postgres  | **5455** |

## Subir com Docker

```bash
docker compose up --build
```

- Web: http://localhost:5180  
- API: http://localhost:8010  
- Postgres: localhost:5455 (`fila` / `fila` / `filaindoor`)

Login seed: `admin@real.local` / `admin123`

### Totem (Sprint 2)

```text
http://localhost:5180/totem/<QUEUE_ID>?token=kiosk-acougue-demo
```

Impressão padrão no Docker: **mock** (`PRINT_PROVIDER=mock`).

### Botoeira (Sprint 3)

```text
http://localhost:5180/operator/<QUEUE_ID>
```

Login operador: `operator@real.local` / `operator123`  
(Selecione o balcão ACOU-1 ou ACOU-2 no topo.)

### Display / TV (Sprint 4)

```text
http://localhost:5180/display/<QUEUE_ID>?token=display-acougue-audio
http://localhost:5180/display/<QUEUE_ID>?token=display-acougue-silent
```

Somente o token `display-acougue-audio` anuncia a senha (TTS).

## Desenvolvimento local

### Banco

```bash
docker compose up -d db
```

### Backend

```bash
cd backend
copy env.example .env   # Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python scripts/seed_data.py
uvicorn app.main:app --reload --port 8010
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App em http://localhost:5180

### Testes

```bash
cd backend
pytest
# concorrência (requer Postgres na 5455):
pytest tests/integration/test_concurrency.py -v
```

## Documentação do módulo

Ver `docs/queue-indoor/`.
