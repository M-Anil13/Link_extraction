# Backend: FastAPI + Playwright. Image pinned to the installed Playwright version.
FROM mcr.microsoft.com/playwright/python:v1.53.0-noble

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Use bundled Chromium (works on ARM64; Google Chrome has no ARM64 Linux build).
# Matches the base image's preinstalled browser, so this is fast.
RUN playwright install chromium

# App code
COPY . .

# Headless on a server (no GUI); interactive login still works via screencast.
ENV HEADLESS=True

# DB config (was read from .env, which is excluded from the image for security).
ENV DATABASE_URL=sqlite+aiosqlite:///./job_automation.db

# Empty = use bundled Chromium (no Chrome channel). Locally defaults to "chrome".
ENV BROWSER_CHANNEL=""

# Render/Railway provide $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
