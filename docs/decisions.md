# Decisions

What was decided, why, and when. Change these only with a reason, and note the change here
(mark reversed decisions as reversed rather than deleting them).

## Scope
- 2026-10-16: Hardening pass on the existing app (bug fixes, security, image size limits,
  schema clean-up, tests). No new user-facing features.

## Platform and hosting
- Two FastAPI services plus Postgres 17 in docker compose. Upload on port 5000, display on
  5001. Postgres is not published to the host; it is reachable only on the compose network.

## Data and secrets
- Credentials and `NOTIFY_TOKEN` come from `.env` (gitignored); `.env.example` is committed.
- Schema: `messages(id, ...)` and `images(id, message_id → messages.id, image)`. Image rows no
  longer duplicate the message text, name, group, event or time.
- Existing databases are upgraded with `migrations/001_ids_and_image_link.sql`, which keeps
  every existing row and also corrects `has_image` to match whether an image is stored.
- The database default timezone is Asia/Hong_Kong (set with `ALTER DATABASE`). The display
  page also converts times to Asia/Hong_Kong in the browser, so it shows the right time
  either way.

## Behaviour and rules
- `/notify` requires the shared `NOTIFY_TOKEN` (header `X-Notify-Token`). If the display
  service has no token configured, it rejects every notify call (fails closed).
- Uploaded photos: files over 15 MB (setting `MAX_UPLOAD_MB`) are rejected and nothing is
  saved. Valid photos are rotated per EXIF, shrunk to fit 1920 px, and stored as JPEG
  quality 85. A file that isn't a valid image: the message is still saved, without the
  photo, with a warning.
- If saving worked but the live notify failed, the upload counts as a success with a warning
  (the message appears when the display page next reloads).
- `limit` on `/messages` is clamped to 1–100 and on `/images` to 1–30 (silently, no error).
- Photos load one at a time (2026-10-18). At the last Thanksgiving event the wall took about a minute to
  show its first photo: `/images` sent 10 full-size photos (~60 MB) in one response and the
  page waited for all of it. Measured on a test copy at 10 Mbit/s: 48.9 s before, 4.0 s after
  with the same full-size photos. `/images` now lists URLs; `/images/{id}` serves each photo
  with a one-year `immutable` cache header (a photo never changes). The page downloads the
  next photo while the current one is shown, since 10 s per photo is ample time. Live uploads
  still arrive inside the WebSocket message (already resized, ~0.4 MB).
- Errors shown to users are generic Chinese text plus a reference ID; details go to the log.

## UI
- All upload and display page text is Traditional Chinese.

## Repository
- Public repo https://github.com/bpy13/thanksgiving-wall, branch `main`, push directly.
