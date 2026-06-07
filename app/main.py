import asyncio
import queue
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.automation.runner import run_application
from app.database.db import engine, Base
from app.utils.logger import setup_logger
from app.utils.otp_store import OTP_STORE
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

    try:
        while True:
            event = await out_queue.get()
            if event.get("type") == "_eof":
                break
            await ws.send_json(event)
    except WebSocketDisconnect:
        stop_flag.set()
    finally:
        input_task.cancel()
        with PROFILE_LOCK:
            ACTIVE_PROFILES.discard(profile)
        try:
            await ws.close()
        except Exception:
            pass
