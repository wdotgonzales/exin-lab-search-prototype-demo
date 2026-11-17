# Exin Lab Search

One searchable interface over scattered lab data. Work in progress.

## Local setup

The app is developed in **WSL (Ubuntu)**. Run every command below inside WSL.

### 1. Install the tools

| Tool | Version | Check |
|---|---|---|
| PostgreSQL + pgvector | 16 | `pg_lsclusters` |
| uv (Python manager) | latest | `uv --version` |
| Node.js | 20.19+ | `node -v` |

```bash
# PostgreSQL 16 + pgvector (official PostgreSQL apt repo)
sudo apt install -y postgresql-common
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
sudo apt install -y postgresql-16 postgresql-16-pgvector

# uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

Install Node.js with your package manager or nvm if `node -v` is missing or below 20.19.

> On Windows, stop any Windows PostgreSQL service so it doesn't take port 5432.

### 2. Create the database

```bash
sudo -u postgres psql -c "CREATE USER exin WITH PASSWORD 'exin_dev';"
sudo -u postgres psql -c "CREATE DATABASE exin_dev OWNER exin;"
sudo -u postgres psql -c "CREATE DATABASE exin_test OWNER exin;"

for db in exin_dev exin_test; do
  sudo -u postgres psql -d "$db" -c "CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS citext; CREATE EXTENSION IF NOT EXISTS pgcrypto;"
done
```

Check:

```bash
psql "postgresql://exin:exin_dev@localhost:5432/exin_dev" -c "\dx"
```

You should see `citext`, `pgcrypto`, `plpgsql` and `vector`.

### 3. Backend

```bash
cd backend
uv sync                      # installs Python 3.12 + all packages into .venv
cp .env.example .env         # then fill in the values below
```

`backend/.env`:

```env
APP_ENV=local
DATABASE_URL=postgresql+psycopg://exin:exin_dev@localhost:5432/exin_dev
JWT_SECRET=<generate one: uv run python -c "import secrets; print(secrets.token_urlsafe(48))">
```

Apply migrations, then run the API:

```bash
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

Check: `curl localhost:8000/api/health` → `{"status":"ok","database":"ok","pgvector":"0.8.7"}`

API docs: http://localhost:8000/docs

> Always run backend commands from the `backend/` folder.

### 4. Frontend

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env         # API_PROXY_TARGET=http://localhost:8000
npm run dev
```

Open http://localhost:5173. The page shows the `/api/health` result.

The Vite dev server forwards `/api/*` to the backend, so the React code never contains a backend URL.

## Database migrations (Alembic)

Run from `backend/`.

| Task | Command |
|---|---|
| Apply all migrations | `uv run alembic upgrade head` |
| Undo the last migration | `uv run alembic downgrade -1` |
| Undo everything | `uv run alembic downgrade base` |
| Show current version | `uv run alembic current` |
| Show history | `uv run alembic history` |

**Adding or changing a table:**

1. Create or edit a model in `app/models/`.
2. Import any new model in `app/models/__init__.py`. Alembic only sees imported models.
3. Generate a migration:
   ```bash
   uv run alembic revision --autogenerate -m "short description"
   ```
4. Review the new file in `migrations/versions/`. Autogenerate is a draft, so check it.
5. Apply it and test that it reverses:
   ```bash
   uv run alembic upgrade head
   uv run alembic downgrade -1
   uv run alembic upgrade head
   ```
6. Commit the model and the migration file together.

> If you see `Target database is not up to date`, a migration exists that hasn't been applied. Run `uv run alembic upgrade head` first.

## Python packages

```bash
uv add <package>           # app dependency
uv add --dev <package>     # dev-only (tests, linting)
```

Commit `pyproject.toml` and `uv.lock` after changes.

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'app'` | Run from `backend/`, not `backend/app/`. |
| `/api/health` returns 503 | Postgres is down: `sudo systemctl start postgresql@16-main` |
| `password authentication failed for user "exin"` | Step 2 wasn't completed, or `DATABASE_URL` has a typo. |
| DBeaver (Windows) can't connect | Use host `127.0.0.1`. If it still fails, run `wsl --shutdown` in PowerShell and reopen WSL. |

**Never commit `.env` files.** Only `.env.example` goes in git.
