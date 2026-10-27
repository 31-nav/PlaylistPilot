# PlaylistPilot — Production & Live Cloud Deployment Guide

This guide details how to run PlaylistPilot in a production environment, expose it live instantly, or deploy it permanently to free cloud hosting platforms.

---

## 1. Instant Live Public URL (Active Right Now)

Your local development server on port 5000 is currently exposed to the internet via secure tunnel:

- **Live URL:** `https://angry-fans-tap.loca.lt`
- **Friendly Password / IP (if prompted by tunnel):** `38.137.52.46`
- **Command to re-launch anytime:**
  ```powershell
  npx -y localtunnel --port 5000
  ```

---

## 2. Production WSGI Server with Waitress (Windows & Linux)

Instead of the development server, you can run PlaylistPilot with **Waitress**, a pure-Python, production-grade WSGI server supporting high concurrency:

```powershell
# Activate environment
.venv\Scripts\activate

# Launch production server
python serve.py
```

By default, Waitress binds to `http://0.0.0.0:5000` with 6 multi-threaded workers.

To customize port and threads:
```powershell
$env:PORT="8080"
$env:WAITRESS_THREADS="10"
python serve.py
```

---

## 3. Free Permanent Cloud Deployment: Render

Render offers free web service hosting for Python web applications.

### Option A: Via GitHub (Recommended)
1. Push this repository to your GitHub account:
   ```bash
   git init
   git add .
   git commit -m "Initial release of PlaylistPilot"
   git remote add origin https://github.com/<your-username>/playlistpilot.git
   git push -u origin main
   ```
2. Log into [Render.com](https://render.com) and click **New &rarr; Web Service**.
3. Select your `playlistpilot` GitHub repository.
4. Render will automatically detect `render.yaml` or you can configure manually:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt gunicorn && python scripts/init_db.py && python scripts/seed_demo_data.py`
   - **Start Command:** `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`
5. Click **Deploy Web Service**. Render will provision your live permanent HTTPS URL (e.g. `https://playlistpilot.onrender.com`).

---

## 4. Free Permanent Cloud Deployment: Railway

Railway provides instantaneous deployment with zero configuration.

1. Install the Railway CLI or visit [Railway.app](https://railway.app).
2. Connect your GitHub repository.
3. Railway automatically detects `railway.json` and `Procfile`.
4. Click **Deploy**. Railway will assign a public domain (e.g. `https://playlistpilot-production.up.railway.app`).

---

## 5. Docker Container Deployment

PlaylistPilot includes a production-ready `Dockerfile` with **FFmpeg** pre-installed and non-root execution.

### Build and Run with Docker Compose

```bash
# Build and start container in detached mode
docker compose up -d --build

# View container logs
docker compose logs -f

# Stop container
docker compose down
```

The container automatically exposes port `5000` and mounts persistent volumes for `./instance` (SQLite database) and `./downloads` (processed media).

### Manual Docker Build

```bash
docker build -t playlistpilot:latest .
docker run -p 5000:5000 -v $(pwd)/instance:/app/instance playlistpilot:latest
```

---

## 6. Production Environment Variables Reference

| Variable | Description | Recommended Production Value |
|---|---|---|
| `FLASK_ENV` | Environment mode | `production` |
| `SECRET_KEY` | Cryptographic session key | A 32-character random string |
| `DATABASE_URL` | SQLite or PostgreSQL URI | `sqlite:///instance/playlistpilot.db` |
| `AUTO_RETRY` | Auto-requeue interrupted jobs | `true` |
| `MAX_RETRIES` | Maximum retry threshold | `3` |
| `QUEUE_POLL_INTERVAL`| Worker polling interval | `2.0` |
| `YOUTUBE_API_KEY` | Optional Google API Key | (Your production key from Google Cloud) |
| `WAITRESS_THREADS` | Number of concurrent request threads | `6` to `16` |
