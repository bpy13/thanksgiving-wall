# Plan: hardening pass (2026-10-16)

**Goal:** fix the bugs found by reading the code, close the open `/notify` endpoint, limit
image sizes, tidy the schema and config, and add tests and lint, without changing what the
pages look like or the JSON the display page reads.

**Approach:** one phase, built directly in this session (no helper agents, at the requester's
instruction). A shared `db.py` provides the connection pool; tests fake the pool and the
display service, so they run offline. The full stack is checked end to end with docker compose.

**Constraints (from `docs/decisions.md`):**
- Two FastAPI services plus Postgres 17 in docker compose. Upload on port 5000, display on
  5001. Postgres is not published to the host.
- Credentials and `NOTIFY_TOKEN` come from `.env` (gitignored); `.env.example` is committed.
- Existing databases are upgraded with `migrations/001_ids_and_image_link.sql`, which keeps
  every existing row.
- All upload and display page text is Traditional Chinese.

**Acceptance criteria:**
1. Bugs 1–9 from the brief are fixed, each covered by a test or a manual check.
2. `/notify` rejects calls without the right token.
3. Photos are rotated, resized to ≤1920 px, stored as JPEG; files over 15 MB are rejected.
4. Credentials live in `.env`; Postgres port not published; `.dockerignore` present.
5. New schema with ids and `message_id`; a migration that preserves rows, tested on an
   old-schema database.
6. `pytest` and `ruff` pass; `docker compose up --build` works end to end.
7. README matches the code.

## Phase 1 – Hardening (built in this session)

- [x] **Task 1: Project setup**
  - Files: CLAUDE.md, docs/decisions.md, docs/open-items.md, this plan, environment.yml,
    pyproject.toml (pytest + ruff config, dev extras), requirements.txt (pinned)
  - Done when: `python -c "import fastapi, psycopg_pool, PIL"` works in env `thanksgiving-wall`

- [x] **Task 2: Shared pool, schema, migration**
  - Files: create db.py, migrations/001_ids_and_image_link.sql; modify init-db/init.sql
  - Done when: init.sql builds the new schema on a fresh postgres:17 container; the migration
    run on an old-schema container with sample rows keeps every row, links each image to its
    message, and a second run is a no-op
  - Notes: `messages.id` and `images.id` are identity primary keys; `images.message_id`
    references `messages(id) ON DELETE CASCADE`. Old rows are matched on identical
    `upload_time` + `message` (both rows were written in one transaction, so their default
    timestamps are equal). Images with no match get a recreated message row. Timezone via
    `ALTER DATABASE <current db> SET timezone = 'Asia/Hong_Kong'`.

- [x] **Task 3: Upload service fixes (bugs 1, 2, 4, 6, 8; token sending)**
  - Files: modify upload.py; test tests/test_upload.py
  - Done when: `pytest tests/test_upload.py` passes, covering: message only; with valid image
    (stored as JPEG ≤1920 px, EXIF rotation applied); invalid image (saved, has_image false,
    warning); oversize (413, nothing saved); notify failure (success + warning, no 500);
    DB failure (generic message with reference ID, no exception text); token header sent
  - Notes: settings `MAX_UPLOAD_MB` (15), `NOTIFY_TOKEN`, `DISPLAY_SERVICE_URL`. Image work
    runs in a thread so it doesn't block other requests. Upload time in the broadcast comes
    from the database row.

- [x] **Task 4: Display service fixes (bugs 3, 5; limit clamp; join query)**
  - Files: modify display.py; test tests/test_display.py
  - Done when: `pytest tests/test_display.py` passes, covering: broadcast skips nobody after a
    dead connection and removes it; `/notify` without/with wrong token → 401; right token
    broadcasts to a real WebSocket client; no token configured → rejected; limits clamped;
    `/images` reads via the join and returns the same keys as before
  - Notes: header `X-Notify-Token`, compared with `secrets.compare_digest`.

- [x] **Task 5: Upload page labels and display page strings (bug 9)**
  - Files: templates/upload.html, templates/display.html
  - Done when: no English user-facing strings left (`Select-String` for "Share Message",
    "Click to choose", "Just now", "Connection error" finds nothing), and the page is checked
    in the running stack
  - Notes: show the server's warning text instead of always saying "wrong image format";
    check file size in the browser before uploading.

- [x] **Task 6: Config, compose, Docker (credentials, bug 7)**
  - Files: docker-compose.yml, .env.example, .gitignore, .dockerignore
  - Done when: `docker compose config` renders with values from `.env`; no 5432 port mapping;
    `.env` ignored by git
  - Notes: postgres healthcheck; services wait for it; `./migrations` mounted read-only into
    the postgres container so the migration can be run with `docker compose exec`.

- [ ] **Task 7: README**
  - Files: README.md
  - Done when: ports 5000/5001, env names match `.env.example`, NOTIFY_TOKEN, migration,
    tests documented; no "thread pool" or other unbacked claims left unchecked

- [ ] **Task 8: End-to-end check with docker compose**
  - Done when: `docker compose up --build`; POST a message and a photo; `/messages` and
    `/images` return them; a WebSocket client on `/ws` receives both broadcasts; `/notify`
    without token → 401; then `docker compose down` (no `-v`)

- [ ] **Task 9: Pre-release review, fixes, ship**
  - Done when: reviewer findings handled (fixed or recorded in open-items), tests and ruff
    pass, pushed to origin main
