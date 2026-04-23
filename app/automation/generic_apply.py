async def apply_generic(page):
    await page.wait_for_load_state("networkidle")

    inputs = await page.query_selector_all("input[type='text'], textarea")

    for input_box in inputs:
        try:
            await input_box.fill("Test Data")
        except:
            continue

    try:
        await page.click("button[type='submit']")
    except:
        pass
