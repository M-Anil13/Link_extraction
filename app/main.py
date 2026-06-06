import asyncio
import threading
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.automation.runner import run_application
from app.database.db import engine, Base
from app.utils.logger import setup_logger
from app.utils.otp_store import OTP_STORE
from extracted_job import extract_links, DEFAULT_OUTPUT_FILE

app = FastAPI(title="Jobright Link Extractor")
logger = setup_logger()

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
async def download(file: str = DEFAULT_OUTPUT_FILE):
    path = Path(file)
    if not path.exists():
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
    queue: asyncio.Queue = asyncio.Queue()
    stop_flag = threading.Event()

    try:
        params = await ws.receive_json()
    except Exception:
        await ws.close()
        return

    profile = params.get("profile", "vamshi")
    max_links = int(params.get("max_links", 31))
    headless = bool(params.get("headless", True))
    output = params.get("output", DEFAULT_OUTPUT_FILE)

    def on_event(etype, payload):
        # Called from the worker thread; hop back to the event loop.
        loop.call_soon_threadsafe(queue.put_nowait, {"type": etype, "payload": payload})

    def worker():
        try:
            extract_links(
                profile=profile,
                max_links=max_links,
                headless=headless,
                output=output,
                on_event=on_event,
                should_stop=stop_flag.is_set,
            )
        except Exception as e:
            loop.call_soon_threadsafe(
                queue.put_nowait, {"type": "error", "payload": {"message": repr(e)}}
            )
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "_eof"})

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    async def listen_for_stop():
        try:
            while True:
                msg = await ws.receive_json()
                if msg.get("action") == "stop":
                    stop_flag.set()
        except Exception:
            stop_flag.set()

    stop_task = asyncio.create_task(listen_for_stop())

    try:
        while True:
            event = await queue.get()
            if event.get("type") == "_eof":
                break
            await ws.send_json(event)
    except WebSocketDisconnect:
        stop_flag.set()
    finally:
        stop_task.cancel()
        try:
            await ws.close()
        except Exception:
            pass
