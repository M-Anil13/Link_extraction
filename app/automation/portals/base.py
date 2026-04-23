from abc import ABC, abstractmethod

class BasePortal(ABC):

    def __init__(self, page, url):
        self.page = page
        self.url = url

    @abstractmethod
    async def open(self):
        pass

    @abstractmethod
    async def apply(self):
        pass

    async def screenshot(self, job_id):
        await self.page.screenshot(path=f"screenshots/{job_id}.png")
