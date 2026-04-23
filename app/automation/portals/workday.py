from .base import BasePortal

class WorkdayPortal(BasePortal):

    async def open(self):
        await self.page.goto(self.url)
        await self.page.wait_for_load_state("networkidle")

    async def apply(self):
        # Placeholder logic
        # Later we add full Workday flow
        await self.page.click("text=Apply")
