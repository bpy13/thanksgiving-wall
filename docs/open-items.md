# Open items

As of 2026-10-16. Tick off, or move to `decisions.md` when settled. A bug that will be fixed goes
here; a limit or trap we live with goes in `known-issues.md`. Each item in one place only.

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
