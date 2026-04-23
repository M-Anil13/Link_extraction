from .generic import GenericPortal
from .workday import WorkdayPortal
from .greenhouse import GreenhousePortal

def get_portal_handler(page, url):

    if "workday" in url:
        return WorkdayPortal(page, url)

    elif "greenhouse" in url:
        return GreenhousePortal(page, url)

    else:
        return GenericPortal(page, url)
