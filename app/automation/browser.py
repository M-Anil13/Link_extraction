from playwright.async_api import async_playwright
import asyncio
from app.utils.otp_store import OTP_STORE

class BrowserManager:
    def __init__(self, headless=False):
        self.headless = headless

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        return self.page

    async def __aexit__(self, exc_type, exc, tb):
        await self.browser.close()


async def handle_universal_otp(page):
    """
    Detects OTP field on any portal and fills it automatically.
    """

    try:
        print("Scanning page for OTP input...")

        # Common OTP selectors
        otp_selectors = [
            "input[type='tel']",
            "input[type='number']",
            "input[name*='otp']",
            "input[name*='code']",
            "input[id*='otp']",
            "input[id*='code']",
            "input[type='text']"
        ]

        otp_input = None

        for selector in otp_selectors:
            elements = await page.query_selector_all(selector)
            if elements:
                otp_input = elements[0]
                break

        if not otp_input:
            print("No OTP input detected.")
            return False

        print("OTP field detected. Waiting for OTP from n8n...")

        for _ in range(30):  # wait 60 sec
            otp_data = OTP_STORE.get("latest")

            if otp_data:
                # Case 1: numeric/alphanumeric OTP
                if otp_data.get("otp"):
                    await otp_input.fill(otp_data["otp"])

                    # Try clicking submit button
                    await page.keyboard.press("Enter")

                    print("OTP submitted.")
                    OTP_STORE.clear()
                    return True

                # Case 2: verification link
                if otp_data.get("verification_link"):
                    await page.goto(otp_data["verification_link"])
                    print("Verification link opened.")
                    OTP_STORE.clear()
                    return True

            await asyncio.sleep(2)

        print("OTP timeout.")
        return False

    except Exception as e:
        print("OTP handler error:", e)
        return False


