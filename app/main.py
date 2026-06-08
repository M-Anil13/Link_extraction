import asyncio
import os
import queue
import random
import re
import threading
import uuid
from pathlib import Path

from datetime import datetime, timedelta

from fastapi import FastAPI, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select, func
from passlib.context import CryptContext

from app.automation.runner import run_application
from app.database.db import engine, Base, AsyncSessionLocal
from app.database.models import User, RunLog
from app.utils.logger import setup_logger
from app.utils.otp_store import OTP_STORE
from app.utils.email import send_email
from extracted_job import extract_links

app = FastAPI(title="Jobright Link Extractor")
logger = setup_logger()

# Per-session outputs live here; one file per run so concurrent users never
# clobber each other's links.
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# A Chrome profile cannot be opened by two Playwright processes at once.
# Guard so a second concurrent run on the same profile is rejected, not crashed.
ACTIVE_PROFILES: set[str] = set()
PROFILE_LOCK = threading.Lock()

# Admin: set ADMIN_KEY env; required to view the admin dashboard data.
ADMIN_KEY = os.getenv("ADMIN_KEY", "")

# Password hashing + email validation.
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
OTP_TTL_MIN = 10


def gen_otp():
    return f"{random.randint(0, 999999):06d}"


async def get_user(db, email):
    return (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()


async def log_run(email, links_saved):
    """Record an extraction run and bump the user's run_count."""
    if not email:
        return
    async with AsyncSessionLocal() as db:
        db.add(RunLog(email=email, links_saved=int(links_saved or 0)))
        row = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if row:
            row.run_count = (row.run_count or 0) + 1
            row.last_seen = datetime.utcnow()
        await db.commit()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten to your frontend origin in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def root():
    return {"message": "Jobright Link Extractor API running"}


@app.post("/apply")
async def apply_job(data: dict):
    return await run_application(data.get("url"))


def _err(status, msg):
    return JSONResponse(status_code=status, content={"ok": False, "error": msg})


@app.post("/auth/signup")
async def auth_signup(data: dict):
    """Register a user; email an OTP to verify the address before they can log in."""
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip() or email.split("@")[0]
    if not EMAIL_RE.match(email):
        return _err(400, "enter a valid email")
    if len(password) < 6:
        return _err(400, "password must be at least 6 characters")

    otp = gen_otp()
    expires = datetime.utcnow() + timedelta(minutes=OTP_TTL_MIN)
    async with AsyncSessionLocal() as db:
        row = await get_user(db, email)
        if row and row.verified:
            return _err(409, "email already registered — please log in")
        if row:  # exists but unverified -> refresh password + OTP
            row.password_hash = pwd_ctx.hash(password)
            row.name = name
            row.otp_code = otp
            row.otp_expires = expires
        else:
            db.add(User(email=email, name=name,
                        password_hash=pwd_ctx.hash(password),
                        verified=False, otp_code=otp, otp_expires=expires))
        await db.commit()

    sent = await asyncio.to_thread(
        send_email, email, "Your NexCV verification code",
        f"Your verification code is {otp}. It expires in {OTP_TTL_MIN} minutes.",
    )
    if not sent:
        return _err(500, "could not send verification email (server email not configured)")
    return {"ok": True, "message": "verification code sent to your email"}


@app.post("/auth/verify")
async def auth_verify(data: dict):
    """Confirm signup with the emailed OTP."""
    email = (data.get("email") or "").strip().lower()
    otp = (data.get("otp") or "").strip()
    async with AsyncSessionLocal() as db:
        row = await get_user(db, email)
        if not row or not row.otp_code:
            return _err(400, "no pending verification for this email")
        if row.otp_expires and datetime.utcnow() > row.otp_expires:
            return _err(400, "code expired — sign up again")
        if otp != row.otp_code:
            return _err(400, "incorrect code")
        row.verified = True
        row.otp_code = None
        row.otp_expires = None
        await db.commit()
    return {"ok": True, "email": email, "name": row.name}


@app.post("/auth/login")
async def auth_login(data: dict):
    """Email + password login against the database (must be verified)."""
    email = (data.get("email") or data.get("username") or "").strip().lower()
    password = data.get("password") or ""
    async with AsyncSessionLocal() as db:
        row = await get_user(db, email)
        if not row or not row.password_hash or not pwd_ctx.verify(password, row.password_hash):
            return _err(401, "invalid email or password")
        if not row.verified:
            return _err(403, "email not verified — check your inbox")
        row.login_count = (row.login_count or 0) + 1
        row.last_seen = datetime.utcnow()
        await db.commit()
        return {"ok": True, "email": row.email, "name": row.name}


@app.post("/auth/forgot")
async def auth_forgot(data: dict):
    """Email an OTP to reset the password."""
    email = (data.get("email") or "").strip().lower()
    async with AsyncSessionLocal() as db:
        row = await get_user(db, email)
        # Always return ok (don't reveal which emails exist).
        if row:
            row.otp_code = gen_otp()
            row.otp_expires = datetime.utcnow() + timedelta(minutes=OTP_TTL_MIN)
            await db.commit()
            await asyncio.to_thread(
                send_email, email, "Your NexCV password reset code",
                f"Your reset code is {row.otp_code}. It expires in {OTP_TTL_MIN} minutes.",
            )
    return {"ok": True, "message": "if that email exists, a reset code was sent"}


@app.post("/auth/reset")
async def auth_reset(data: dict):
    """Set a new password using the emailed reset OTP."""
    email = (data.get("email") or "").strip().lower()
    otp = (data.get("otp") or "").strip()
    new_password = data.get("new_password") or ""
    if len(new_password) < 6:
        return _err(400, "password must be at least 6 characters")
    async with AsyncSessionLocal() as db:
        row = await get_user(db, email)
        if not row or not row.otp_code:
            return _err(400, "no reset request for this email")
        if row.otp_expires and datetime.utcnow() > row.otp_expires:
            return _err(400, "code expired — request again")
        if otp != row.otp_code:
            return _err(400, "incorrect code")
        row.password_hash = pwd_ctx.hash(new_password)
        row.verified = True
        row.otp_code = None
        row.otp_expires = None
        await db.commit()
    return {"ok": True, "message": "password updated — you can log in"}


@app.post("/auth/change-password")
async def auth_change_password(data: dict):
    """Change password while logged in (email + old + new)."""
    email = (data.get("email") or "").strip().lower()
    old_password = data.get("old_password") or ""
    new_password = data.get("new_password") or ""
    if len(new_password) < 6:
        return _err(400, "new password must be at least 6 characters")
    async with AsyncSessionLocal() as db:
        row = await get_user(db, email)
        if not row or not pwd_ctx.verify(old_password, row.password_hash or ""):
            return _err(401, "current password is incorrect")
        row.password_hash = pwd_ctx.hash(new_password)
        await db.commit()
    return {"ok": True, "message": "password changed"}


@app.get("/admin/users")
async def admin_users(x_admin_key: str = Header(default="")):
    """Admin: list users + usage. Requires header X-Admin-Key == ADMIN_KEY."""
    if not ADMIN_KEY or x_admin_key != ADMIN_KEY:
        return JSONResponse(status_code=401, content={"ok": False, "error": "unauthorized"})
    async with AsyncSessionLocal() as db:
        users = (await db.execute(select(User).order_by(User.last_seen.desc()))).scalars().all()
        total_runs = (await db.execute(select(func.count(RunLog.id)))).scalar() or 0
        total_links = (await db.execute(select(func.coalesce(func.sum(RunLog.links_saved), 0)))).scalar() or 0
    return {
        "ok": True,
        "total_users": len(users),
        "total_runs": total_runs,
        "total_links": total_links,
        "users": [
            {
                "email": u.email,
                "name": u.name,
                "login_count": u.login_count,
                "run_count": u.run_count,
                "first_seen": u.first_seen.isoformat() if u.first_seen else None,
                "last_seen": u.last_seen.isoformat() if u.last_seen else None,
            }
            for u in users
        ],
    }


@app.post("/submit-otp")
async def submit_otp(data: dict):
    OTP_STORE["latest"] = {
        "otp": data.get("otp"),
        "verification_link": data.get("verificationLink"),
    }
    return {"status": "received"}


@app.get("/download")
async def download(file: str):
    # Only allow files inside OUTPUT_DIR (block path traversal).
    path = (OUTPUT_DIR / Path(file).name).resolve()
    if path.parent != OUTPUT_DIR.resolve() or not path.exists():
        return {"error": "file not found"}
    return FileResponse(
        path,
        filename=path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.websocket("/ws/extract")
async def ws_extract(ws: WebSocket):
    """Run the extractor in a worker thread and stream events to the client.

    Client -> server: {profile, max_links, headless} to start; {action:"stop"}.
    Server -> client: event objects {type, payload}.
    """
    await ws.accept()
    loop = asyncio.get_running_loop()
    out_queue: asyncio.Queue = asyncio.Queue()   # events -> client
    input_queue: queue.Queue = queue.Queue()     # input <- client (thread-safe)
    stop_flag = threading.Event()

    try:
        params = await ws.receive_json()
    except Exception:
        await ws.close()
        return

    profile = params.get("profile", "vamshi")
    max_links = int(params.get("max_links", 31))
    headless = bool(params.get("headless", True))
    interactive = bool(params.get("interactive", True))
    user_email = params.get("email")  # for usage tracking

    # Reject a concurrent run on the same profile (Chrome locks the dir).
    with PROFILE_LOCK:
        if profile in ACTIVE_PROFILES:
            await ws.send_json({"type": "error", "payload": {
                "message": f"Profile '{profile}' is already running. "
                           f"Use a different profile."}})
            await ws.close()
            return
        ACTIVE_PROFILES.add(profile)

    # Unique output file per session.
    session_id = uuid.uuid4().hex[:12]
    output_name = f"{session_id}.xlsx"
    output = str(OUTPUT_DIR / output_name)
    await ws.send_json({"type": "session", "payload": {
        "session_id": session_id, "download": f"/download?file={output_name}"}})

    def on_event(etype, payload):
        # Called from the worker thread; hop back to the event loop.
        loop.call_soon_threadsafe(
            out_queue.put_nowait, {"type": etype, "payload": payload}
        )

    def worker():
        try:
            extract_links(
                profile=profile,
                max_links=max_links,
                headless=headless,
                interactive=interactive,
                input_queue=input_queue,
                output=output,
                on_event=on_event,
                should_stop=stop_flag.is_set,
            )
        except Exception as e:
            loop.call_soon_threadsafe(
                out_queue.put_nowait, {"type": "error", "payload": {"message": repr(e)}}
            )
        finally:
            loop.call_soon_threadsafe(out_queue.put_nowait, {"type": "_eof"})

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    # Client -> server: stop + interactive-login input (click/key/char/...).
    INPUT_TYPES = {"click", "move", "scroll", "char", "key", "login_done"}

    async def listen_for_input():
        try:
            while True:
                msg = await ws.receive_json()
                if msg.get("action") == "stop":
                    stop_flag.set()
                elif msg.get("type") in INPUT_TYPES:
                    input_queue.put(msg)
        except Exception:
            stop_flag.set()

    input_task = asyncio.create_task(listen_for_input())

    # Heartbeat: keep the WebSocket busy during long quiet periods (e.g. a slow
    # card) so proxies (HF/Cloudflare) don't drop it as idle.
    async def heartbeat():
        try:
            while True:
                await asyncio.sleep(20)
                await ws.send_json({"type": "ping", "payload": {}})
        except Exception:
            pass

    heartbeat_task = asyncio.create_task(heartbeat())

    try:
        while True:
            event = await out_queue.get()
            if event.get("type") == "_eof":
                break
            if event.get("type") == "done":
                # Record usage for this run.
                try:
                    await log_run(user_email, event.get("payload", {}).get("saved"))
                except Exception:
                    pass
            await ws.send_json(event)
    except WebSocketDisconnect:
        stop_flag.set()
    finally:
        input_task.cancel()
        heartbeat_task.cancel()
        with PROFILE_LOCK:
            ACTIVE_PROFILES.discard(profile)
        try:
            await ws.close()
        except Exception:
            pass
