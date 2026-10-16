# Open items

As of 2026-10-16. Tick off, or move to `decisions.md` when settled. Each item in one place only.

## Blockers

## Waiting on the user
1. **Rotate the burned database password.** The old password was committed to the public
   repo in `docker-compose.yml` and is still in git history, so treat it as known to anyone.
   On any live deployment: put a new password in `.env`, then change it inside Postgres too
   (a new `.env` value alone does not change an existing volume's password):
   `docker compose exec postgres psql -U admin -d thanksgiving -c "ALTER USER admin PASSWORD '<new>'"`.
2. **Run the migration on any existing deployment** (see README, "Upgrading an existing
   database"). Take a `pg_dump` backup first.

3. **Unknown file `docs/plans/2026-10-16-robustness.md`.** An empty file with this name
   appeared in the repo during the 2026-10-16 run, created by another process (not this
   run). It was left on disk, untracked and uncommitted. Delete it or keep it, your call.

## Pending work

## Later
4. **iPhone HEIC photos.** Pillow can't read HEIC without the `pillow-heif` add-on. Most
   phone browsers convert to JPEG when uploading through a web form, so this is usually
   fine; if members report "not a valid image" from iPhones, add `pillow-heif`.
5. **Visual check in a browser.** The 2026-10-16 run checked both pages by fetching their
   HTML and driving the API and WebSocket from a script, not by looking at them in a browser.
   Worth a quick look on a phone and the projector before the next meeting.
6. **Old photos stay full size.** The migration keeps photos uploaded before 2026-10-16 as
   they were (full size, possibly PNG although the page labels them JPEG). With many large
   old photos, `/images` responses can be big. Option: a one-off script to re-encode them.
7. **Upload size is checked after the file arrives.** The 15 MB cap stops the photo being
   stored, but the server still receives the whole request first. Low risk on a church
   network; a reverse proxy with a request-size limit would close it.
8. **The migration has no automated test.** It was tested by hand on an old-schema
   Postgres container (rows kept, images linked, second run a no-op).
