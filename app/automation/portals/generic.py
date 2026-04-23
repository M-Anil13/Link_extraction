import json
from app.ai.form_mapper import map_form_fields
from app.automation.portals.base import BasePortal

class GenericPortal(BasePortal):

    async def open(self):
        await self.page.goto(self.url)
        await self.page.wait_for_load_state("networkidle")

    async def apply(self):

        elements = await self.page.query_selector_all("input, textarea")

        labels = []

        for el in elements:
            name = await el.get_attribute("name")
            placeholder = await el.get_attribute("placeholder")

            if name:
                labels.append(name)
            elif placeholder:
                labels.append(placeholder)

        # Load profile
        with open("app/ai/profile.json") as f:
            profile_data = json.load(f)

        # Ask AI to map fields
        mapping = map_form_fields(labels, profile_data)

        # Fill fields dynamically
        for el in elements:
            name = await el.get_attribute("name")
            placeholder = await el.get_attribute("placeholder")

            key = name if name else placeholder

            if key in mapping:
                try:
                    await el.fill(str(mapping[key]))
                except:
                    continue

        # Try submit
        try:
            await self.page.click("button[type='submit']")
        except:
            pass
        
