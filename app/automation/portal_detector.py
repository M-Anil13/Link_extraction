def detect_portal(url: str):
    if "workday" in url:
        return "workday"
    elif "greenhouse" in url:
        return "greenhouse"
    elif "lever.co" in url:
        return "lever"
    else:
        return "generic"
