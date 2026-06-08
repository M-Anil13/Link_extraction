# Local-Live Deployment (Docker + Cloudflare Tunnel + Vercel)

Run the backend on your own machine, expose it publicly with a free Cloudflare
tunnel, and serve the frontend from Vercel. Zero cost, no credit card.

```
Browser  ->  Vercel (frontend)  ->  Cloudflare Tunnel  ->  Docker (backend)  ->  Jobright
                                                            on YOUR machine
```

---

## What survives closing the VS Code window?

| Piece | Closes with VS Code? | Notes |
|-------|----------------------|-------|
| **Docker container** | ❌ No — keeps running | Managed by Docker Desktop. `--restart unless-stopped` also survives reboot. |
| **Cloudflare tunnel** | ✅ Yes, if run in the VS Code terminal | Run it in a **standalone PowerShell window** (or as a service) so it survives. |

So: Docker is fine. Run the **tunnel in its own PowerShell window**, not inside VS Code.

---

## One-time setup

1. Install Docker Desktop, Node, and cloudflared (`winget install --id Cloudflare.cloudflared`).
2. Stop the laptop from sleeping: Settings → Power → Sleep = **Never**; lid close = **Do nothing**.

---

## Start everything (every boot)

### 1. Build the backend image (only after code changes)
```powershell
$env:DOCKER_BUILDKIT=0
docker build -t jobright-backend .
```

### 2. Run the backend container (detached, auto-restart)
```powershell
# create the DB file once so Docker mounts a file (not a folder)
if (-not (Test-Path job_automation.db)) { New-Item -ItemType File job_automation.db }

docker run -d --restart unless-stopped -p 8000:8000 `
  -e APP_USERS="naniyadav1312@gmail.com:Pass@123,anil:anil123" `
  -e ADMIN_KEY="nexcv-admin-secret" `
  -v ${PWD}/chrome-profiles:/app/chrome-profiles `
  -v ${PWD}/outputs:/app/outputs `
  -v ${PWD}/job_automation.db:/app/job_automation.db `
  --name jobright jobright-backend
```
Verify:
```powershell
docker ps                 # shows 'jobright' Up, 0.0.0.0:8000->8000
curl http://localhost:8000   # {"message":"Jobright Link Extractor API running"}
```

### Auth & Admin (IMPORTANT)

These are **environment variables you choose** and pass with `-e` above. They are
NOT stored in any file — that keeps passwords out of the repo. Whatever you set
here is what users / admin type.

| Env | Purpose | Example |
|-----|---------|---------|
| `APP_USERS` | Login accounts, `user:pass` comma-separated. Username must match exactly at login. | `anil:anil123,raj:raj456` |
| `ADMIN_KEY` | Password for the `/admin` dashboard. | `nexcv-admin-secret` |

- **User login:** go to `/login`, use a username + password from `APP_USERS`.
- **Admin dashboard:** go to `/admin`, enter the `ADMIN_KEY` value.
- To change users/admin key: edit the `-e` values, then
  `docker rm -f jobright` and re-run the `docker run` command above.
- If login says "Login failed": the backend image is old (rebuild step 1) or the
  username/password don't match `APP_USERS`.

### 3. Start the Cloudflare tunnel (in a SEPARATE PowerShell window)
```powershell
& "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:8000
```
It prints a URL like:
```
https://xxxx-words.trycloudflare.com
```
Leave this window open. **This URL changes every time the tunnel restarts.**

### 4. Point Vercel at the tunnel URL
- Vercel -> frontend project -> Settings -> Environment Variables
- `VITE_API_URL = https://xxxx-words.trycloudflare.com`  (no trailing slash)
- Deployments -> Redeploy

### 5. Use it
Open the Vercel site (e.g. `link-extraction.vercel.app`) -> set profile + max
links -> Start. The login panel streams; log in; links extract live.

---

## Restarting

- **Restart backend:** `docker restart jobright`
- **Stop backend:** `docker stop jobright`   |  **Start:** `docker start jobright`
- **Restart tunnel:** Ctrl+C in its window, re-run step 3.
  > After a tunnel restart the URL changes -> update Vercel `VITE_API_URL` + redeploy.

---

## Common issues

| Symptom | Cause / Fix |
|---------|-------------|
| `port is already allocated` | Old container on 8000. `docker stop $(docker ps -q)` then re-run. |
| `cloudflared not recognized` | New terminal, or use full path `C:\Program Files (x86)\cloudflared\cloudflared.exe`. |
| Frontend "connection lost" | Tunnel down or URL changed. Restart tunnel, update Vercel env. |
| Vercel 500 / FUNCTION_INVOCATION_FAILED | Vercel Root Directory must be `frontend`. |

---

## Limitations (local-live)

- Up only while your machine + Docker + tunnel are running. Sleep/shutdown/Wi-Fi
  drop = down.
- Quick-tunnel URL is not fixed; changes on restart.
- For a permanent URL: create a **named Cloudflare tunnel** (free Cloudflare
  account + a domain) — then the URL never changes and you set Vercel once.

---

## Make it true 24/7 (later)

1. **Named tunnel** for a fixed URL (needs a domain on Cloudflare).
2. Run cloudflared **as a Windows service** so it starts on boot:
   `cloudflared service install` (with a named tunnel config).
3. Docker already auto-starts via `--restart unless-stopped` + Docker Desktop
   "start on login".
