# Thanksgiving Wall – notes for Claude

A live thanksgiving message and photo wall used at church meetings. Members open the upload
page on their phones and post a message (and optionally a photo); a projector shows the
display page, which updates live over a WebSocket. The UI is in Traditional Chinese.

Read these before substantial changes:

- `docs/decisions.md` – what was decided and why (don't re-litigate without a reason)
- `docs/open-items.md` – pending work and questions waiting on the user
- `docs/plans/` – the latest plan
- `README.md` – user-facing setup and commands

## Environment
- Install: `conda env create -f environment.yml` (env `thanksgiving-wall`), or
  `conda activate thanksgiving-wall; pip install -e ".[dev]"`
- Run (full stack): copy `.env.example` to `.env`, fill it in, then `docker compose up --build`
  (upload page http://localhost:5000, display page http://localhost:5001)
- Tests: `conda activate thanksgiving-wall; pytest`
- Lint: `ruff check .` and `ruff format --check .`

## Project rules
- Secrets live only in `.env` (gitignored). `.env.example` holds placeholders.
- The password once committed in `docker-compose.yml` is burned; never reuse it.
- `init-db/init.sql` only runs on a fresh Postgres volume. Any schema change also needs a
  numbered file in `migrations/` for existing databases, documented in the README.
- Never run `docker compose down -v` on a volume you didn't create; it deletes the wall's data.
- Runtime dependencies are listed twice: `requirements.txt` (Docker image, pinned) and
  `pyproject.toml` (local dev, minimum versions). Keep them in step.

## Conventions
- `db.py` holds the shared Postgres pool; each app opens it in its lifespan and stores it on
  `app.state.pool`. Tests replace `app.state.pool` with a fake (see `tests/conftest.py`).
- Messages shown to users are Chinese; log details server-side and return a generic message
  with a short reference ID.
- The upload service calls the display service's `/notify` with the `X-Notify-Token` header.
