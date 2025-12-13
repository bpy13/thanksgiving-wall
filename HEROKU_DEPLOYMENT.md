# Heroku Deployment Guide

## Summary of Changes

Your app has been **combined into a single service** for simpler Heroku deployment:

### What Changed:
1. **Created `app.py`** - Combines both upload and display services into one FastAPI application
   - Upload page: `/` (root)
   - Display page: `/display`
   - All other endpoints remain the same

2. **Database Connection** - Now supports both Heroku and local development
   - Uses `DATABASE_URL` environment variable (Heroku)
   - Falls back to individual env vars for local Docker

3. **New Files Created:**
   - `heroku.yml` - Heroku manifest for Docker deployment
   - `Procfile` - Process definition (backup if not using heroku.yml)
   - `release-tasks.sh` - Automatic database initialization on deploy
   - `app.json` - App metadata and one-click deploy config
   - `.slugignore` - Optimize deployment size

4. **Updated `Dockerfile`** - Added curl for streaming release logs

## Deployment Steps

### Option 1: Deploy with Heroku CLI

```bash
# 1. Install Heroku CLI if you haven't
# https://devcenter.heroku.com/articles/heroku-cli

# 2. Login to Heroku
heroku login

# 3. Create a new Heroku app
heroku create your-app-name

# 4. Set the stack to container
heroku stack:set container -a your-app-name

# 5. Add PostgreSQL addon (if not auto-created by heroku.yml)
heroku addons:create heroku-postgresql:essential-0 -a your-app-name

# 6. Deploy
git push heroku master

# 7. Open your app
heroku open -a your-app-name
```

### Option 2: Deploy via Heroku Dashboard

1. Go to https://dashboard.heroku.com/
2. Click "New" → "Create new app"
3. Connect your GitHub repository
4. Enable automatic deploys from master branch
5. Click "Deploy Branch"

### Option 3: One-Click Deploy

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

## URLs After Deployment

Assuming your Heroku app is named `your-app-name`:

- **Upload Page**: `https://your-app-name.herokuapp.com/`
- **Display Page**: `https://your-app-name.herokuapp.com/display`

## Local Testing

You can still test locally with Docker Compose:

```bash
# Use the original docker-compose.yml
docker-compose up -d

# Upload page: http://localhost:5000
# Display page: http://localhost:5001
```

Or test with the new combined app:

```bash
# Set environment variables
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=thanksgiving
export POSTGRES_USER=admin
export POSTGRES_PASSWORD=20anniversary

# Run the combined app
uvicorn app:app --host 0.0.0.0 --port 8000

# Upload page: http://localhost:8000/
# Display page: http://localhost:8000/display
```

## Environment Variables

The app automatically detects the environment:

- **Heroku**: Uses `DATABASE_URL` (set automatically by PostgreSQL addon)
- **Local**: Uses individual `POSTGRES_*` environment variables

## Monitoring

```bash
# View logs
heroku logs --tail -a your-app-name

# Check dyno status
heroku ps -a your-app-name

# View database info
heroku pg:info -a your-app-name
```

## Troubleshooting

**Issue: Release phase fails**
- Check logs: `heroku logs --tail -a your-app-name`
- Ensure PostgreSQL addon is provisioned: `heroku addons -a your-app-name`

**Issue: WebSocket connection fails**
- Heroku supports WebSockets on all dyno types
- Ensure your client connects to `wss://` (not `ws://`) in production

**Issue: Images not displaying**
- Check database size: `heroku pg:info -a your-app-name`
- Consider upgrading PostgreSQL plan if storing many large images

## Cost Estimation

- **Eco Dyno**: $5/month (sleeps after 30 min of inactivity)
- **Basic Dyno**: $7/month (never sleeps)
- **PostgreSQL Essential-0**: $5/month (10M rows, 64 GB storage)

**Total**: ~$10-12/month for a production-ready setup

## Migration Notes

If you have existing upload/display URLs:
- Old upload URL (`port 5000`) → New: `/`
- Old display URL (`port 5001`) → New: `/display`

Update any hardcoded URLs or bookmarks accordingly!
