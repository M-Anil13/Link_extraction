import argparse
import os
import queue
import re
import sys
import time
from pathlib import Path

from openpyxl import Workbook, load_workbook
from playwright.sync_api import sync_playwright

# Configure UTF-8 encoding for stdout on Windows to prevent UnicodeEncodeError with emojis
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# --- Selectors -------------------------------------------------------------
APPLY_RE = re.compile(r"^\s*Apply( Now| With Autofill)?\s*$", re.I)
MANUAL_RE = re.compile(
    r"Apply Without Customizing|Apply Manually|Apply on company|Apply directly|External Apply|Apply Site|Visit Company Site|Go to Application",
    re.I,
)
YES_APPLIED_RE = re.compile(r"^\s*Yes, I applied!?|I applied\s*$", re.I)
LOGGED_OUT_RE = re.compile(
    r"sign\s*in|sign\s*up|log\s*in|login|get started|continue with", re.I
)


def apply_buttons(page):
    """All fresh Apply buttons in the feed (excludes 'Applied')."""
    return page.get_by_role("button", name=APPLY_RE)


def manual_buttons(page):
    return (
        page.get_by_role("button", name=MANUAL_RE)
        .or_(page.get_by_role("link", name=MANUAL_RE))
        .or_(page.get_by_text(MANUAL_RE))
    )


def yes_applied_buttons(page):
    return page.get_by_role("button", name=YES_APPLIED_RE)


DEFAULT_PROFILE = "vamshi"
DEFAULT_MAX_LINKS = 31
DEFAULT_START_URL = "https://jobright.ai"
DEFAULT_OUTPUT_FILE = "filtered_job_links.xlsx"

POPUP_TIMEOUT = 6000        # wait for a new tab to open after manual apply
LOAD_TIMEOUT = 8000         # wait for a page to finish loading
MANUAL_BTN_TIMEOUT = 3500   # wait for the "Apply Manually" / "Apply Without Customizing" button
MODAL_SETTLE = 600          # small settle after opening a modal

# Interactive login (CDP screencast) — fixed viewport so frame pixels == page
# coordinates 1:1, making click/key replay from the browser accurate.
LOGIN_VIEWPORT = {"width": 1280, "height": 800}
LOGIN_TIMEOUT_S = 300       # max seconds to wait for the user to finish login

# A single feed card can stall (embed with no new tab, confirm button missing).
# After this many no-progress passes on the same first card, force past it.
MAX_STUCK_PER_CARD = 3

BLOCK_KEYWORDS = [
    "Security Clearance",
    "U.S. Citizen Only",
]

BLOCK_PORTAL_DOMAINS = [
    "linkedin.com",
    "glassdoor.com",
    "monster.com",
    "ziprecruiter.com",
    "jobright.ai",
    "simplyhired.com",
    "careerbuilder.com",
    "hackajob.com",
]

ATS_DOMAINS = [
    "myworkdayjobs.com",
    "workday.com",
    "greenhouse.io",
    "boards.greenhouse.io",
    "lever.co",
    "jobs.lever.co",
    "icims.com",
    "smartrecruiters.com",
    "successfactors.com",
    "taleo.net",
    "myworkday.com",
    "jobvite.com",
    "bamboohr.com",
    "recruitee.com",
    "applicantpro.com",
    "brassring.com",
    "paylocity.com",
    "workforcenow.adp.com",
    "oraclecloud.com",
    "dayforcehcm.com",
    "ceridian.com",
    "ats.rippling.com",
    "rippling.com",
]


def is_application_url(url):
    """Accept every external apply link EXCEPT LinkedIn (and jobright itself).

    Previously this only accepted known ATS/path patterns and dropped the rest.
    Now we save any external link; only LinkedIn and the jobright.ai source site
    are excluded.
    """
    if not url:
        return False
    u = url.lower()
    if "linkedin.com" in u:
        return False
    if "jobright.ai" in u:  # source site, not a real external application
        return False
    return True


def safe_wait_load(pg, timeout=LOAD_TIMEOUT):
    """wait_for_load_state with a bounded timeout. Never raises.

    The original code called wait_for_load_state() with the default 30s and no
    try/except, so a blank/slow popup hung the whole run and then crashed.
    """
    try:
        pg.wait_for_load_state("domcontentloaded", timeout=timeout)
    except Exception:
        pass


def load_existing(output_file):
    """Resume: read previously saved URLs from a sheet (per-session, no globals).

    Returns (collected_links list, saved_links set). Safe if file missing.
    """
    collected, saved = [], set()
    path = Path(output_file)
    if not path.exists():
        return collected, saved
    try:
        wb = load_workbook(path, read_only=True)
        ws = wb.active
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or len(row) < 2:
                continue
            url = row[1]
            if url and url not in saved:
                saved.add(url)
                collected.append(url)
        wb.close()
        print(f"Resume: loaded {len(collected)} existing links from {output_file}")
    except Exception as e:
        print("Resume: could not read existing file -", repr(e))
    return collected, saved


def save_to_excel(output_file, collected_links):
    path = Path(output_file)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Filtered Job Links"
    ws.append(["S.No", "Job URL"])

    for i, link in enumerate(collected_links, start=1):
        ws.append([i, link])

    wb.save(output_file)
    print(f"Saved {output_file}")


def try_load_more_jobs(page, previous_total):
    """Trigger infinite scroll and return True when more jobs are loaded."""
    try:
        apply_buttons(page).last.scroll_into_view_if_needed(timeout=3000)
    except Exception:
        pass

    page.mouse.wheel(0, 2600)
    page.wait_for_timeout(1200)

    new_total = apply_buttons(page).count()
    print(f"DEBUG: jobs before scroll={previous_total}, after scroll={new_total}")
    return new_total > previous_total


def click_yes_applied_fast(page):
    """Click Jobright's 'Yes, I applied!' confirm so the card leaves the feed."""
    try:
        btn = yes_applied_buttons(page).first
        if btn.count() > 0:
            btn.click(force=True, timeout=800)
            return True
    except Exception:
        pass
    return False


def dismiss_modal(page):
    """Best-effort close of any open Jobright modal."""
    if not click_yes_applied_fast(page):
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
    page.wait_for_timeout(400)


def dismiss_overlays(page):
    """Remove popups that float over the feed and block Apply clicks.
    Strips Trustpilot, rating modals ('Enjoying Jobright?'), consent banners, and masks.
    """
    try:
        page.evaluate(
            """() => {
                const sel = [
                    // Jobright marketing / promos / feedback
                    '[class*="trustpilot"]', '[class*="promotion"]', '[class*="promo-card"]',
                    '[class*="trial-promotion"]', '[class*="upgrade"]', '[class*="paywall"]',
                    '[class*="premium-modal"]', '[class*="newsletter"]', '[class*="subscribe-modal"]',
                    '[class*="feedback"]', '[class*="rating"]', '[class*="enjoying"]',
                    // cookie / consent banners
                    '[class*="cookie"]', '[class*="consent"]', '[id*="cookie"]',
                    // onboarding tours
                    '.ant-tour', '[class*="onboarding"]', '[class*="-tour"]',
                    // drawer overlays
                    '.ant-drawer', '.ant-drawer-mask',
                    // 3rd-party chat / survey widgets
                    '[id*="intercom"]', '[class*="intercom"]',
                    '.crisp-client', '#crisp-chatbox',
                    '[class*="drift"]', '[class*="hotjar"]', '[id*="hj_feedback"]'
                ].join(',');
                document.querySelectorAll(sel).forEach(e => {
                    if (e.innerText && e.innerText.includes("Enjoying Jobright")) {
                        e.remove();
                    } else if (!e.classList.contains("ant-modal")) {
                        e.remove();
                    }
                });
            }"""
        )
    except Exception:
        pass
    try:
        close_btn = page.locator(".ant-modal-close, [aria-label='Close']:visible").first
        if close_btn.count() > 0:
            modal_text = page.locator(".ant-modal-body").inner_text(timeout=300) or ""
            if "Enjoying Jobright" in modal_text or "Rating" in modal_text:
                close_btn.click(force=True, timeout=500)
    except Exception:
        pass


def extract_external_url(context, page):
    """Return the external application URL after clicking manual apply.

    Handles four Jobright flows:
      1. Explicit 'Apply Without Customizing / Apply Manually' button/link in modal
      2. External <a> link directly inside modal dialog
      3. New tab popup opened on click
      4. Same-tab navigation away from jobright.ai
    """
    modal = page.locator(".ant-modal:visible, [role='dialog']:visible").last

    # Strategy 1: Look for explicit manual apply button/link inside modal or page
    target_btn = None
    if modal.count() > 0:
        btn_in_modal = manual_buttons(modal)
        if btn_in_modal.count() > 0:
            target_btn = btn_in_modal.first
    if target_btn is None:
        btn_on_page = manual_buttons(page)
        if btn_on_page.count() > 0:
            target_btn = btn_on_page.first

    if target_btn is not None:
        try:
            target_btn.wait_for(timeout=MANUAL_BTN_TIMEOUT)
            url = capture_new_tab_url(context, page, target_btn, timeout=POPUP_TIMEOUT)
            if url:
                return url
        except Exception:
            pass

    # Strategy 2: Look for external <a> href directly inside modal
    if modal.count() > 0:
        try:
            links = modal.locator("a[href]").all()
            for lnk in links:
                href = lnk.get_attribute("href") or ""
                if href.startswith("http") and "jobright.ai" not in href.lower() and "linkedin.com" not in href.lower():
                    return href
        except Exception:
            pass

    # Strategy 3: Check for stray extra tab or main page nav
    if len(context.pages) > 1:
        new_page = context.pages[-1]
        safe_wait_load(new_page)
        url = new_page.url
        if "jobright.ai" not in (url or "").lower():
            return url
    if "jobright.ai" not in (page.url or "").lower():
        return page.url

    return None


def close_extra_tabs(context, keep_page):
    """Close leftover application tabs so they don't pile up / get re-read."""
    for pg in list(context.pages):
        if pg is keep_page:
            continue
        try:
            pg.close()
        except Exception:
            pass


def capture_new_tab_url(context, page, click_locator, timeout=POPUP_TIMEOUT):
    """Click something that opens the company site in a new tab; return its URL.

    Falls back to a stray extra tab or a same-tab navigation. None if nothing.
    """
    try:
        with context.expect_page(timeout=timeout) as new_page_info:
            click_locator.click(force=True)
        new_page = new_page_info.value
        safe_wait_load(new_page)
        return new_page.url
    except Exception:
        pass
    if len(context.pages) > 1:
        np = context.pages[-1]
        safe_wait_load(np)
        return np.url
    return None


def jobright_process(context, page, emit, save_link):
    dismiss_overlays(page)

    btn = apply_buttons(page).first
    if btn.count() == 0:
        return False

    try:
        btn.click(timeout=6000)
    except Exception:
        dismiss_overlays(page)
        try:
            btn.click(force=True, timeout=3000)
        except Exception:
            return False

    page.wait_for_timeout(MODAL_SETTLE)

    # Restriction keywords check inside opened modal
    scope_text = ""
    try:
        modal = page.locator(".ant-modal:visible, [role='dialog']:visible").last
        if modal.count() > 0:
            scope_text = modal.inner_text(timeout=1000)
    except Exception:
        scope_text = ""

    if scope_text and any(k in scope_text for k in BLOCK_KEYWORDS):
        emit("skip", {"reason": "restricted"})
        dismiss_modal(page)
        return True

    job_url = extract_external_url(context, page)
    page.bring_to_front()

    if job_url:
        save_link(job_url)          # emits portal/duplicate/link
        dismiss_modal(page)
        return True

    emit("skip", {"reason": "no-url"})
    dismiss_modal(page)
    return False


# ---- Naukri source (SCAFFOLD — selectors need tuning from screenshots) ----
# Naukri flow (to confirm): recommended/search jobs -> each card/detail has an
# "Apply" button -> external jobs open the company site in a NEW TAB (that URL
# is what we save); "Apply on company site" is the external variant.
NAUKRI_START_URL = "https://www.naukri.com/mnjuser/recommendedjobs"
NAUKRI_APPLY_RE = re.compile(r"^\s*Apply( on company site)?\s*$", re.I)
NAUKRI_LOGGED_OUT_RE = re.compile(r"login|register|sign\s*in", re.I)


def naukri_apply_buttons(page):
    # TODO: confirm real selector from a logged-in Naukri screenshot.
    return page.get_by_role("button", name=NAUKRI_APPLY_RE).or_(
        page.get_by_role("link", name=NAUKRI_APPLY_RE)
    )


def naukri_logged_in(page, wait_ms=5000):
    # Logged in if apply targets exist and no login/register CTA is shown.
    try:
        if page.get_by_role("link", name=NAUKRI_LOGGED_OUT_RE).count() > 0:
            return False
    except Exception:
        pass
    try:
        naukri_apply_buttons(page).first.wait_for(timeout=wait_ms)
        return True
    except Exception:
        return False


def naukri_process(context, page, emit, save_link):
    try:
        btn = naukri_apply_buttons(page).first
        # External apply opens a new tab -> capture that URL.
        url = capture_new_tab_url(context, page, btn)
    except Exception:
        url = None
    page.bring_to_front()
    if url:
        save_link(url)
        # TODO: Naukri may show a confirm dialog; press Escape to move on.
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        return True
    emit("skip", {"reason": "no-url"})
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    return False


# ---- LinkedIn source (HIGH ban/ToS risk) -----------------------------------
# Flow: /jobs/collections/recommended (= "Show all") shows a job LIST (left) +
# DETAIL panel (right). Click a card -> detail loads -> its apply button is
# either "Easy Apply" (internal, skip) or "Apply" (external, opens the company
# site in a NEW TAB -> save that URL). Dismiss (X) the card so the next becomes
# first; that also means we never reprocess the same job.
LINKEDIN_START_URL = "https://www.linkedin.com/jobs/collections/recommended/"
LINKEDIN_EASY_RE = re.compile(r"easy apply", re.I)
LINKEDIN_SIGNIN_RE = re.compile(r"^\s*sign in\s*$", re.I)


def linkedin_job_cards(page):
    # Job cards in the left results list (several class variants over time).
    return page.locator(
        "li.scaffold-layout__list-item, div.job-card-container, [data-job-id]"
    )


def linkedin_logged_in(page, wait_ms=6000):
    try:
        if page.get_by_role("link", name=LINKEDIN_SIGNIN_RE).count() > 0:
            return False
    except Exception:
        pass
    try:
        linkedin_job_cards(page).first.wait_for(timeout=wait_ms)
        return True
    except Exception:
        return False


def linkedin_dismiss_card(card):
    """Remove a processed card so the next one becomes first (no reprocessing)."""
    try:
        x = card.get_by_role("button", name=re.compile(r"dismiss|hide|remove", re.I)).first
        if x.count() > 0:
            x.click(force=True, timeout=1500)
    except Exception:
        pass


def linkedin_process(context, page, emit, save_link):
    cards = linkedin_job_cards(page)
    if cards.count() == 0:
        return False
    card = cards.first
    try:
        card.scroll_into_view_if_needed(timeout=2000)
        card.click(timeout=4000)          # load the detail panel on the right
        page.wait_for_timeout(1200)
    except Exception:
        linkedin_dismiss_card(card)
        return True

    # Apply button in the detail panel.
    apply_btn = page.locator("button.jobs-apply-button, .jobs-apply-button").first
    try:
        label = apply_btn.inner_text(timeout=1500) or ""
    except Exception:
        label = ""

    if not label:
        emit("skip", {"reason": "no-apply"})
    elif LINKEDIN_EASY_RE.search(label):
        emit("skip", {"reason": "easy-apply"})
    else:
        # External apply -> opens the company site in a new tab.
        url = capture_new_tab_url(context, page, apply_btn)
        page.bring_to_front()
        if url:
            save_link(url)              # emits portal/duplicate/link
        else:
            emit("skip", {"reason": "no-url"})

    linkedin_dismiss_card(card)
    page.wait_for_timeout(500)
    return True


SOURCES = {
    "jobright": {
        "start_url": DEFAULT_START_URL,
        "logged_in": lambda page: is_logged_in(page),
        "quick_login": lambda page: (not logged_out_markers(page)
                                     and apply_buttons(page).count() > 0),
        "count": lambda page: apply_buttons(page).count(),
        "load_more": lambda page, total: try_load_more_jobs(page, total),
        "process": jobright_process,
        "dismiss": dismiss_modal,
    },
    "naukri": {
        "start_url": NAUKRI_START_URL,
        "logged_in": lambda page: naukri_logged_in(page),
        "quick_login": lambda page: naukri_apply_buttons(page).count() > 0,
        "count": lambda page: naukri_apply_buttons(page).count(),
        "load_more": lambda page, total: try_load_more_jobs(page, total),
        "process": naukri_process,
        "dismiss": lambda page: page.keyboard.press("Escape"),
    },
    "linkedin": {
        "start_url": LINKEDIN_START_URL,
        "logged_in": lambda page: linkedin_logged_in(page),
        "quick_login": lambda page: linkedin_job_cards(page).count() > 0,
        "count": lambda page: linkedin_job_cards(page).count(),
        "load_more": lambda page, total: try_load_more_jobs(page, total),
        "process": linkedin_process,
        "dismiss": lambda page: page.keyboard.press("Escape"),
    },
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract external job application links from Jobright.ai."
    )
    parser.add_argument(
        "--profile",
        default=DEFAULT_PROFILE,
        help=(
            "Profile name or path for persistent Chrome data. "
            "If name is provided, folder is created inside ./chrome-profiles/."
        ),
    )
    parser.add_argument(
        "--max-links",
        type=int,
        default=DEFAULT_MAX_LINKS,
        help="Maximum number of unique application links to save.",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_START_URL,
        help="Starting URL (default: https://jobright.ai).",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_FILE,
        help="Excel output file name/path.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode.",
    )
    parser.add_argument(
        "--login-wait",
        type=int,
        default=300,
        help="Maximum time in seconds to wait for manual login in non-interactive mode (default: 300).",
    )
    return parser.parse_args()


def resolve_profile_dir(profile_arg):
    profile_path = Path(profile_arg)
    if profile_path.is_absolute() or profile_path.parent != Path("."):
        target = profile_path
    else:
        target = Path("chrome-profiles") / profile_arg

    target.mkdir(parents=True, exist_ok=True)
    return str(target.resolve())


def logged_out_markers(page):
    """True if auth CTAs (Sign in / Log in / Get started) are on the page."""
    try:
        if page.get_by_role("button", name=LOGGED_OUT_RE).count() > 0:
            return True
        if page.get_by_role("link", name=LOGGED_OUT_RE).count() > 0:
            return True
    except Exception:
        pass
    return False


def is_logged_in(page, wait_ms=5000):
    """Logged in = jobs feed Apply buttons present AND no auth CTA visible.

    The public landing page has a marketing 'Apply Now' button, so checking
    Apply buttons alone gives a false positive; the auth-CTA check rules it out.
    """
    if logged_out_markers(page):
        return False
    try:
        apply_buttons(page).first.wait_for(timeout=wait_ms)
        return not logged_out_markers(page)
    except Exception:
        return False


def interactive_login(context, page, emit, input_queue, stop_requested,
                      quick_login=None, site_label="the site",
                      timeout_s=LOGIN_TIMEOUT_S):
    """Stream the page to the UI (CDP screencast) and replay user input until
    login completes. Returns True once the jobs feed appears or the user
    signals done. No VNC/Docker needed — pure CDP.
    """
    if quick_login is None:
        quick_login = lambda pg: (not logged_out_markers(pg)
                                  and apply_buttons(pg).count() > 0)
    cdp = context.new_cdp_session(page)
    frames = queue.Queue()

    def on_frame(params):
        frames.put(params)

    cdp.on("Page.screencastFrame", on_frame)
    cdp.send("Page.startScreencast", {
        "format": "jpeg", "quality": 55,
        "maxWidth": LOGIN_VIEWPORT["width"], "maxHeight": LOGIN_VIEWPORT["height"],
        "everyNthFrame": 1,
    })
    emit("need_login", {"message": f"Log in to {site_label} in the panel.",
                        "width": LOGIN_VIEWPORT["width"],
                        "height": LOGIN_VIEWPORT["height"]})

    start = time.time()
    done = False
    try:
        while time.time() - start < timeout_s and not stop_requested():
            page.wait_for_timeout(120)  # pump CDP events + input

            # Push the most recent frame to the UI (drop stale ones).
            last = None
            while not frames.empty():
                params = frames.get()
                last = params.get("data")
                try:
                    cdp.send("Page.screencastFrameAck",
                             {"sessionId": params.get("sessionId")})
                except Exception:
                    pass
            if last:
                emit("frame", {"data": last})

            # Replay queued user input from the browser.
            while input_queue is not None and not input_queue.empty():
                ev = input_queue.get()
                etype = ev.get("type")
                try:
                    if etype == "click":
                        page.mouse.click(ev["x"], ev["y"])
                    elif etype == "move":
                        page.mouse.move(ev["x"], ev["y"])
                    elif etype == "scroll":
                        page.mouse.wheel(0, ev.get("dy", 0))
                    elif etype == "char":
                        page.keyboard.type(ev["value"])
                    elif etype == "key":
                        page.keyboard.press(ev["value"])
                    elif etype == "login_done":
                        done = True
                except Exception as e:
                    emit("error", {"message": f"input replay: {e!r}"})
                if done:
                    break

            # Quick, non-blocking completion check (avoid 5s wait per tick).
            if done or quick_login(page):
                done = True
                break
    finally:
        try:
            cdp.send("Page.stopScreencast")
        except Exception:
            pass

    if done:
        emit("login_ok", {"message": "Login detected. Starting extraction..."})
    return done


def extract_links(
    profile=DEFAULT_PROFILE,
    max_links=DEFAULT_MAX_LINKS,
    url=None,
    output=DEFAULT_OUTPUT_FILE,
    headless=False,
    login_wait=300,
    interactive=False,
    input_queue=None,
    on_event=None,
    should_stop=None,
    source="jobright",
):
    """Core extraction. Emits structured events via on_event(type, payload).

    Event types: status, found, link, skip, done, error, stopped.
    `should_stop()` (optional) is polled each loop so a UI can cancel.
    Runs synchronously; call from a worker thread when used inside async code.
    """
    def emit(etype, payload=None):
        msg = f"[{etype}] {payload if payload is not None else ''}"
        try:
            print(msg)
        except Exception:
            try:
                print(msg.encode("ascii", "replace").decode("ascii"))
            except Exception:
                pass
        if on_event:
            try:
                on_event(etype, payload or {})
            except Exception:
                pass

    def stop_requested():
        return bool(should_stop and should_stop())

    cfg = SOURCES.get(source, SOURCES["jobright"])
    if url is None:
        url = cfg["start_url"]

    # Per-run state (no module globals -> safe for concurrent sessions).
    collected_links, saved_links = load_existing(output)
    emit("status", {"message": "Resumed existing links",
                    "links": list(collected_links)})

    profile_dir = resolve_profile_dir(profile)

    # Interactive mode streams the page to the UI, so it must run headless with
    # a fixed viewport (frame pixels map 1:1 to page coordinates).
    if interactive:
        launch_kwargs = dict(headless=True, viewport=LOGIN_VIEWPORT)
    else:
        launch_kwargs = dict(headless=headless, args=["--start-maximized"])

    # Browser channel: "chrome" locally (real Chrome), empty in Docker/ARM
    # so Playwright uses bundled Chromium. Set BROWSER_CHANNEL env to override.
    channel = os.getenv("BROWSER_CHANNEL", "chrome")
    if channel:
        launch_kwargs["channel"] = channel

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            **launch_kwargs,
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto(url)
        emit("status", {"message": f"Opened {url} (profile: {profile})"})

        if not cfg["logged_in"](page):
            if interactive:
                ok = interactive_login(context, page, emit, input_queue,
                                       stop_requested,
                                       quick_login=cfg["quick_login"],
                                       site_label=source)
                if not ok:
                    emit("error", {"message": "Login not completed."})
                    context.close()
                    emit("done", {"saved": 0, "attempts": 0,
                                  "total": len(collected_links)})
                    return list(collected_links)
            else:
                # Non-interactive: give a visible browser time for manual login.
                timeout_s = int(login_wait / 1000) if login_wait > 1000 else int(login_wait)
                if headless:
                    emit("error", {"message": "Not logged in. Run without --headless to log in manually in Chrome."})
                    context.close()
                    emit("done", {"saved": 0, "attempts": 0,
                                  "total": len(collected_links)})
                    return list(collected_links)

                emit("status", {"message": f"Not logged in. Please log in to {source} in the opened browser window (waiting up to {timeout_s}s)..."})
                start_login = time.time()
                logged_in = False
                while time.time() - start_login < timeout_s:
                    if stop_requested():
                        break
                    try:
                        page.wait_for_timeout(1000)
                        if cfg["quick_login"](page) or cfg["logged_in"](page):
                            logged_in = True
                            break
                    except Exception:
                        # Browser window or context was closed by user
                        break

                if not logged_in:
                    emit("error", {"message": f"Not logged in (no jobs found after waiting {timeout_s}s)."})
                    context.close()
                    emit("done", {"saved": 0, "attempts": 0,
                                  "total": len(collected_links)})
                    return list(collected_links)
                else:
                    emit("status", {"message": "Login detected!"})

        emit("status", {"message": "Jobs detected. Extracting..."})

        # Shared save routine (filter/dedupe/write/count/emit) — same per source.
        counters = {"saved": 0}

        def save_link(job_url):
            if not is_application_url(job_url):
                emit("skip", {"reason": "portal", "url": job_url})
                return "portal"
            if job_url in saved_links:
                emit("skip", {"reason": "duplicate", "url": job_url})
                return "dup"
            saved_links.add(job_url)
            collected_links.append(job_url)
            save_to_excel(output, collected_links)
            counters["saved"] += 1
            emit("link", {"url": job_url, "index": counters["saved"],
                          "max": max_links})
            return "new"

        attempts = 0
        no_new_job_rounds = 0
        max_no_new_job_rounds = 5
        stuck_on_card = 0

        while counters["saved"] < max_links:
            if stop_requested():
                emit("stopped", {"saved": counters["saved"]})
                break

            total = cfg["count"](page)

            if total == 0:
                loaded = cfg["load_more"](page, total)
                if loaded:
                    no_new_job_rounds = 0
                    continue
                no_new_job_rounds += 1
                if no_new_job_rounds >= max_no_new_job_rounds:
                    emit("status", {"message": "No more jobs after scrolling."})
                    break
                continue

            no_new_job_rounds = 0
            attempts += 1
            emit("progress", {"attempt": attempts, "saved": counters["saved"],
                              "max": max_links, "stuck": stuck_on_card})

            made_progress = False
            try:
                made_progress = cfg["process"](context, page, emit, save_link)
            except Exception as e:
                emit("error", {"message": repr(e)})
                try:
                    cfg["dismiss"](page)
                except Exception:
                    pass

            close_extra_tabs(context, page)
            page.wait_for_timeout(400)

            if made_progress:
                stuck_on_card = 0
            else:
                stuck_on_card += 1
                if stuck_on_card >= MAX_STUCK_PER_CARD:
                    emit("status", {"message": "Card stuck - scrolling past."})
                    page.mouse.wheel(0, 1200)
                    page.wait_for_timeout(800)
                    stuck_on_card = 0

        context.close()

    save_to_excel(output, collected_links)
    emit("done", {"saved": counters["saved"], "attempts": attempts,
                  "total": len(collected_links)})
    return list(collected_links)


def run():
    args = parse_args()
    extract_links(
        profile=args.profile,
        max_links=args.max_links,
        url=args.url,
        output=args.output,
        headless=args.headless,
        login_wait=args.login_wait,
    )


if __name__ == "__main__":
    run()
