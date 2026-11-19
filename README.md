# Exin Lab Search

Exin Lab Search is a web app that keeps a lab's documents in one place. You can upload files (PDF, Word, Excel, CSV, Markdown, text), find them by name, type or date, read them in the browser, and ask an AI assistant questions that it answers from the documents, showing which file each answer came from. Admins can also delete files and see an activity history.

**Live demo:** https://exin-therapeutics.bubble-pop-rush.fyi

**Stack:** React + TypeScript (Vite) · FastAPI · PostgreSQL + pgvector · OpenAI · AWS (EC2, RDS, S3)

## Documentation

- [User Guide](https://drive.google.com/file/d/1RwwKjPJf0-8k7nUbpe-I0MRgjTiSptUB/view): how to use the app, step by step
- [Technical Design](https://drive.google.com/file/d/1zvezQqMv9tbIka_3DG0wfZxsCrdy5NOc/view): architecture, database, features and deployment

## Local setup

Developed on WSL (Ubuntu). You need:

- PostgreSQL 16 with pgvector
- [uv](https://docs.astral.sh/uv/)
- Node.js 20.19+

### 1. Database

```bash
sudo -u postgres psql -c "CREATE USER exin WITH PASSWORD 'exin_dev';"
sudo -u postgres psql -c "CREATE DATABASE exin_dev OWNER exin;"
sudo -u postgres psql -c "CREATE DATABASE exin_test OWNER exin;"

for db in exin_dev exin_test; do
  sudo -u postgres psql -d "$db" -c "CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS citext; CREATE EXTENSION IF NOT EXISTS pgcrypto;"
done
```

### 2. Environment files

**`backend/.env`** (start from the example):

```bash
cd backend
cp .env.example .env
```

```env
APP_ENV=local
DATABASE_URL=postgresql+psycopg://exin:exin_dev@localhost:5432/exin_dev
JWT_SECRET=<at least 32 characters, e.g. from: python3 -c "import secrets; print(secrets.token_urlsafe(48))">

STORAGE_BACKEND=local
LOCAL_STORAGE_DIR=storage

EMBEDDING_BACKEND=fake
# OPENAI_API_KEY=sk-...
```

**`frontend/.env`**:

```env
API_PROXY_TARGET=http://localhost:8000
```

Never commit `.env` files.

### 3. Backend

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

Check: `curl localhost:8000/api/health` should return `"status":"ok"`. API docs are at http://localhost:8000/docs.

### 4. Create an account

There is no sign-up page. Create users from the command line (it asks for a password, 12+ characters):

```bash
cd backend
uv run python -m app.cli create-user --email admin@example.com --name "Admin User" --role admin
uv run python -m app.cli create-user --email viewer@example.com --name "Viewer User" --role viewer
```

### 5. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and sign in.

### 6. Uploads

With `STORAGE_BACKEND=local`, uploaded files are saved in `backend/storage/` (git ignores this folder). No AWS account is needed.

Files are read by a background worker. Run it in another terminal, or uploads stay at *Waiting to index*:

```bash
cd backend
uv run python -m app.worker
```

Sample files to upload are in `seed-data/`.

### 7. AI assistant (optional)

The assistant, meaning search and file summaries need an OpenAI API key.

- **No key:** keep `EMBEDDING_BACKEND=fake`. Upload, browse, filter, read and delete all work. Don't use the chat button, because it needs a key.
- **With a key:** set these in `backend/.env`, then restart the API and the worker:

  ```env
  EMBEDDING_BACKEND=openai
  OPENAI_API_KEY=sk-...
  ```

  Choose this before uploading. Files uploaded while it was `fake` won't have real search data.

## Tests

Create `backend/.env.test` pointing at the test database (tests refuse to run on any database not ending in `_test`):

```env
DATABASE_URL=postgresql+psycopg://exin:exin_dev@localhost:5432/exin_test
JWT_SECRET=test-secret-at-least-32-characters-long
```

```bash
cd backend && uv run pytest
cd frontend && npm test
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `No module named 'app'` | Run backend commands from `backend/`. |
| `/api/health` returns 503 | Start Postgres: `sudo systemctl start postgresql@16-main` |
| `password authentication failed` | Check step 1 and `DATABASE_URL`. |
| Files stay at *Waiting to index* | The worker isn't running (step 6). |
| Chat shows an error | `OPENAI_API_KEY` is missing (step 7). |
