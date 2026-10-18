# Thanksgiving Wall

A real-time thanksgiving message and photo sharing application built for church meetings. Members can upload thanksgiving messages with photos, and all submissions are displayed live on a slideshow with a YouTube-like layout.

## Features

- **Real-time Display**: WebSocket-powered live updates - new submissions appear instantly
- **Photo Slideshow**: Automatic rotation of uploaded photos with message overlays
- **YouTube-like Layout**: 75% images section, 25% message feed
- **Smart Queue System**: Priority display for new uploads, seamless rotation
- **Chinese Interface**: Traditional Chinese throughout; times shown in Hong Kong time (GMT+8)

## Architecture

### Services
- **Upload Server** (port 5000): the form members use; validates and resizes photos, saves to the database
- **Display Server** (port 5001): serves the live display page, manages WebSocket connections
- **PostgreSQL 17**: stores messages and photos; reachable only by the two services (not published to the host)
- **Docker Compose**: runs all three

### Real-time Flow
1. A member submits a message (and optional photo) → the upload server checks the photo, saves the message and photo to the database
2. The upload server calls the display server's `/notify` endpoint, with the shared `NOTIFY_TOKEN`
3. The display server pushes the new message over WebSocket to every open display page

## Quick Start

### Prerequisites
- Docker with Docker Compose
- At least 1 GB RAM

### Deployment
```powershell
git clone https://github.com/bpy13/thanksgiving-wall
cd thanksgiving-wall
# Create your settings file and fill in real values (see "Configuration")
Copy-Item .env.example .env
notepad .env
# Start all services
docker compose up -d --build
# Upload page:  http://localhost:5000
# Display page: http://localhost:5001
```
(On macOS/Linux use `cp .env.example .env` and your editor of choice.)

Members' phones open the upload page using the host computer's network address, e.g.
`http://192.168.1.20:5000`.

## Usage

### For Congregation Members
1. Visit the upload URL on your phone/tablet
2. Fill in your thanksgiving message (required)
3. Add your name, group and event (optional)
4. Attach a photo (optional, up to 15 MB)
5. Submit - your message appears on the main display instantly!

### For Display Management
1. Open the display URL on the presentation screen
2. Messages appear in real-time on the right sidebar
3. Photos rotate automatically every 10 seconds on the left
4. New photos get priority display and join the rotation
5. When the rotation runs out, the page fetches a fresh random set of photos

## Configuration

### Environment variables (`.env`)
All settings live in `.env` (never committed). `.env.example` lists them:

| Variable | Required | Meaning |
|---|---|---|
| `POSTGRES_USER` | yes | Database user (existing deployments: keep `admin`) |
| `POSTGRES_PASSWORD` | yes | Database password |
| `POSTGRES_DB` | yes | Database name (existing deployments: keep `thanksgiving`) |
| `NOTIFY_TOKEN` | yes | Shared secret the upload server sends to the display server's `/notify`. Any long random string: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `MAX_UPLOAD_MB` | no (15) | Largest photo file accepted |
| `DISPLAY_SERVICE_URL` | no | Where the upload server finds the display server (default `http://display-server:5001`) |

`POSTGRES_HOST` and `POSTGRES_PORT` are set inside `docker-compose.yml`.

### `/notify` token
The display server only accepts `/notify` calls that carry the header
`X-Notify-Token: <NOTIFY_TOKEN>`. Without it, anyone on the church network could post to the
wall. If `NOTIFY_TOKEN` is missing, `docker compose` refuses to start.

### Photos
Uploaded photos are checked with Pillow, turned upright using the phone's orientation data,
shrunk to fit within 1920 × 1920 pixels and stored as JPEG (quality 85). Files over
`MAX_UPLOAD_MB` are refused with a message. A file that isn't a picture is skipped: the
message is still posted, with a warning. The resizing runs in a worker thread so other
uploads aren't held up.

### Database Schema
- **messages**: `id`, `message`, `has_image`, `user_name`, `group_name`, `event`, `upload_time`
- **images**: `id`, `message_id` (→ `messages.id`), `image` (JPEG bytes)
- **Timezone**: the database default is Asia/Hong_Kong; the display page also converts times to Hong Kong time

### Display limits
- `/messages?limit=` returns the latest messages (default 20, at most 100)
- `/images?limit=` returns a random set of photos (default 10, at most 30): the message
  details and a URL for each photo, not the photo itself
- `/images/{id}` returns one photo; the browser keeps it, so it is downloaded only once
- Photo rotation every 10 seconds (set in `templates/display.html`). The wall downloads each
  photo just before its turn, while the previous one is on screen, so the first photo appears
  as soon as it has arrived instead of after the whole set.

## Upgrading an existing database

`init-db/init.sql` only runs the first time the database volume is created. A wall set up
before October 2026 has the old tables (no ids; photos stored with copies of the message
details). Upgrade it once with the migration, which keeps every existing message and photo:

```powershell
# 1. Stop the app services (Postgres keeps running), then back up.
#    The backup holds every message and photo: it is saved outside the repo folder so it
#    can't end up in git or the Docker image.
docker compose stop upload-server display-server
docker compose exec postgres sh -c 'pg_dump -U $POSTGRES_USER $POSTGRES_DB > /tmp/backup.sql'
docker compose cp postgres:/tmp/backup.sql ..\thanksgiving-backup.sql
# 2. Get the new version's files (git pull), create .env (see Configuration), then
#    start Postgres with the new settings (mounts the migrations folder)
docker compose up -d postgres
# 3. Run the migration
docker compose exec postgres sh -c 'psql -v ON_ERROR_STOP=1 -U $POSTGRES_USER -d $POSTGRES_DB -f /migrations/001_ids_and_image_link.sql'
# 4. Only now start the new app version (it needs the new tables)
docker compose up -d --build
```
It prints `Migration 001 applied.` (or `already applied` if run again; running it twice is
safe). It also corrects `has_image` on old messages whose attached file wasn't a valid image.

### Changing the database password
Changing `POSTGRES_PASSWORD` in `.env` does not change the password inside an existing
database. Change both (replace `admin` / `thanksgiving` if your names differ):
```powershell
docker compose exec postgres psql -U admin -d thanksgiving -c "ALTER USER admin PASSWORD 'new-password'"
# then put the same password in .env and restart the app services
docker compose up -d --force-recreate upload-server display-server
```

## Privacy & Security

- **Local storage**: all data stays in the self-hosted PostgreSQL database
- **No external APIs**: no third-party services or data sharing
- **Photo checks**: Pillow verifies and re-encodes every photo; non-images are not stored
- **Database not exposed**: Postgres has no published port
- **Errors**: members see a short Chinese message with a reference number; details are in the server log (`docker compose logs upload-server`)

### Backups
```powershell
docker compose exec postgres sh -c 'pg_dump -U $POSTGRES_USER $POSTGRES_DB > /tmp/backup.sql'
docker compose cp postgres:/tmp/backup.sql ..\thanksgiving-backup.sql
```

## Development

Local setup (Windows, conda):
```powershell
conda env create -f environment.yml
conda activate thanksgiving-wall
pytest                 # tests (no database or Docker needed; both are faked)
ruff check .           # lint
ruff format --check .  # formatting
```

- Upload service: `upload.py` and `templates/upload.html`
- Display service: `display.py` and `templates/display.html`
- Shared database pool: `db.py`
- Database: `init-db/init.sql` for new databases, plus a numbered file in `migrations/` for existing ones

## Troubleshooting

```powershell
docker compose ps                       # container status
docker compose logs upload-server       # also: display-server, postgres
docker compose restart
```
Reset the database (**deletes every message and photo**):
```powershell
docker compose down -v
docker compose up -d
```

### Network Issues
- Ports 5000 and 5001 must be reachable from members' phones (check the host's firewall)
- Members must be on the same network as the host computer

## License

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
