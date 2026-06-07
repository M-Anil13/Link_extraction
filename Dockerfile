# Backend: FastAPI + Playwright. Image pinned to the installed Playwright version.
FROM mcr.microsoft.com/playwright/python:v1.53.0-noble

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The app launches Chrome via channel="chrome", so install the Chrome channel.
RUN playwright install chrome

# App code
COPY . .

# Headless on a server (no GUI); interactive login still works via screencast.
ENV HEADLESS=True

# Render/Railway provide $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
