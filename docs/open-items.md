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

## Pending work

## Later
4. **iPhone HEIC photos.** Pillow can't read HEIC without the `pillow-heif` add-on. Most
   phone browsers convert to JPEG when uploading through a web form, so this is usually
   fine; if members report "not a valid image" from iPhones, add `pillow-heif`.
5. **Check on a real phone and the projector.** Headless Chrome (2026-10-16) at phone size
   (390×844) and projector size (1920×1080): the form posted a message with a photo, labels
   stayed Chinese after reset, and the wall showed the photo, message, group, 圖片 tag and
   Hong Kong time live. Still worth a look on an actual phone and the church projector. The
   only console error was a missing favicon (harmless 404).
6. **Old photos stay full size.** The migration keeps photos uploaded before 2026-10-16 as
   they were (full size, possibly PNG although the page labels them JPEG). With many large
   old photos, `/images` responses can be big. Option: a one-off script to re-encode them.
7. **Upload size is checked after the file arrives.** The 15 MB cap stops the photo being
   stored, but the server still receives the whole request first. Low risk on a church
   network; a reverse proxy with a request-size limit would close it.
8. **The migration has no automated test.** It was tested by hand on an old-schema
   Postgres container (rows kept, images linked, second run a no-op).
