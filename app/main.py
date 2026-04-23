from fastapi import FastAPI
from app.automation.runner import run_application
from app.database.db import engine, Base
from app.utils.logger import setup_logger
import asyncio
from typing import Optional
from app.utils.otp_store import OTP_STORE



app = FastAPI()
logger = setup_logger()
OTP_STORE = {}

@app.post("/apply")
async def apply_job(data: dict):
    url = data.get("url")
    result = await run_application(url)
    return result


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
async def root():
    return {"message": "Database Connected 🚀"}


@app.post("/submit-otp")
async def submit_otp(data: dict):
    OTP_STORE["latest"] = {
        "otp": data.get("otp"),
        "verification_link": data.get("verificationLink")
    }
    return {"status": "received"}
app = FastAPI()

@app.post("/submit-otp")
async def submit_otp(data: dict):
    print("Received OTP:", data)

    OTP_STORE["latest"] = {
        "otp": data.get("otp"),
        "verification_link": data.get("verificationLink")
    }

    return {"status": "OTP stored"}
