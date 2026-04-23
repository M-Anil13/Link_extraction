from .browser import BrowserManager
from .portal_detector import detect_portal
from .generic_apply import apply_generic
from app.config import HEADLESS
import asyncio
from app.utils.logger import setup_logger
from sqlalchemy import insert
from app.database.models import JobApplication
from app.database.db import AsyncSessionLocal
from app.automation.browser import BrowserManager
from app.automation.portals.factory import get_portal_handler
from app.automation.browser import handle_universal_otp



logger = setup_logger()
MAX_RETRIES = 2

async def run_application(url: str):

    async with AsyncSessionLocal() as db:

        job = JobApplication(job_url=url, status="started")
        db.add(job)
        await db.commit()
        await db.refresh(job)

        for attempt in range(MAX_RETRIES + 1):
            try:
                logger.info(f"Attempt {attempt+1} for {url}")

                async with BrowserManager(headless=HEADLESS) as page:

                    portal_handler = get_portal_handler(page, url)

                    await portal_handler.open()
                    await portal_handler.apply()
                    await portal_handler.screenshot(job.id)

                job.status = "completed"
                await db.commit()

                return {"status": "completed"}

            except Exception as e:
                logger.error(str(e))

                if attempt == MAX_RETRIES:
                    job.status = "failed"
                    await db.commit()
                    return {"status": "failed"}

                await asyncio.sleep(3)

async def run_application(url: str):

    async with AsyncSessionLocal() as db:

        job = JobApplication(job_url=url, status="started")
        db.add(job)
        await db.commit()
        await db.refresh(job)

        for attempt in range(MAX_RETRIES + 1):
            try:
                logger.info(f"Attempt {attempt+1} for {url}")

                async with BrowserManager(headless=HEADLESS) as page:

                    portal_handler = get_portal_handler(page, url)

                    await portal_handler.open()
                    await portal_handler.apply()

                    # 🔐 UNIVERSAL OTP HANDLER HERE
                    await handle_universal_otp(page)

                    await portal_handler.screenshot(job.id)

                job.status = "completed"
                await db.commit()

                return {"status": "completed"}

            except Exception as e:
                logger.error(str(e))

                if attempt == MAX_RETRIES:
                    job.status = "failed"
                    await db.commit()
                    return {"status": "failed"}

                await asyncio.sleep(3)
