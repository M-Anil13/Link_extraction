import argparse
from pathlib import Path

from openpyxl import Workbook
from playwright.sync_api import sync_playwright

collected_links = []
saved_links = set()

# Edit these defaults if you want to control behavior directly in code.
DEFAULT_PROFILE = "vamshi"
DEFAULT_MAX_LINKS = 31
DEFAULT_START_URL = "https://jobright.ai"
DEFAULT_OUTPUT_FILE = "filtered_job_links.xlsx"

# Short, explicit timeouts (ms). Default Playwright load wait is 30s -> hangs.
POPUP_TIMEOUT = 6000        # wait for a new tab to open after manual apply
LOAD_TIMEOUT = 8000         # wait for a page to finish loading
MANUAL_BTN_TIMEOUT = 600    # wait for the "Apply Manually" button
MODAL_SETTLE = 600          # small settle after opening a modal

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
    if not url:
        return False
    u = url.lower()
    if any(domain in u for domain in BLOCK_PORTAL_DOMAINS):
        return False
    if any(domain in u for domain in ATS_DOMAINS):
        return True
    if "/apply" in u or "application" in u:
        return True

    # Practical fallback: accept direct career/job posting paths.
    job_path_markers = [
        "/jobs/",
        "/job/",
        "/careers/",
        "/positions/",
        "/openings/",
        "/p/",
    ]
    if any(marker in u for marker in job_path_markers):
        return True
    return False


def safe_wait_load(pg, timeout=LOAD_TIMEOUT):
    """wait_for_load_state with a bounded timeout. Never raises.

    The original code called wait_for_load_state() with the default 30s and no
    try/except, so a blank/slow popup hung the whole run and then crashed.
    """
    try:
        pg.wait_for_load_state("domcontentloaded", timeout=timeout)
    except Exception:
        pass


def save_to_excel(output_file):
    wb = Workbook()
    ws = wb.active
    ws.title = "Filtered Job Links"
    ws.append(["S.No", "Job URL"])

    for i, link in enumerate(collected_links, start=1):
        ws.append([i, link])

    wb.save(output_file)
    print(f"Saved {output_file}")


def try_load_more_jobs(page, apply_selector, previous_total):
    """Trigger infinite scroll and return True when more jobs are loaded."""
    try:
        page.locator(apply_selector).last.scroll_into_view_if_needed(timeout=3000)
    except Exception:
        pass

    page.mouse.wheel(0, 2600)
    page.wait_for_timeout(1200)

    new_total = page.locator(apply_selector).count()
    print(f"DEBUG: jobs before scroll={previous_total}, after scroll={new_total}")
    return new_total > previous_total


def click_yes_applied_fast(page):
    """Click Jobright's 'Yes, I applied!' confirm so the card leaves the feed."""
    selectors = [
        "button:has-text('Yes, I applied!')",
        "button:has-text('Yes, I applied')",
        "button:has-text('I applied')",
    ]
    for selector in selectors:
        try:
            btn = page.locator(selector).first
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


def extract_external_url(context, page):
    """Return the external application URL after clicking manual apply.

    Handles three Jobright flows, all bounded by short timeouts:
      1. New tab opens (workday / icims / rippling)         -> read new tab url
      2. Inline embed, no new tab (greenhouse /embed/...)   -> read current url
      3. Same-tab navigation away from jobright             -> read page url
    """
    manual_apply_button = page.locator(
        "button:has-text('No, Apply Manually'), "
        "button:has-text('Apply Manually'), "
        "button:has-text('Apply Without Customizing')"
    )

    # Flow 1: manual button present -> expect a popup tab.
    try:
        manual_apply_button.first.wait_for(timeout=MANUAL_BTN_TIMEOUT)
        try:
            with context.expect_page(timeout=POPUP_TIMEOUT) as new_page_info:
                manual_apply_button.first.click(force=True)
            new_page = new_page_info.value
            safe_wait_load(new_page)
            return new_page.url
        except Exception:
            # Button clicked but no popup (inline embed / same-tab nav).
            page.wait_for_timeout(MODAL_SETTLE)
    except Exception:
        # No manual button at all.
        pass

    # Flow 2/3: check for a stray extra tab, else current page if it left jobright.
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
    return parser.parse_args()


def resolve_profile_dir(profile_arg):
    profile_path = Path(profile_arg)
    if profile_path.is_absolute() or profile_path.parent != Path("."):
        target = profile_path
    else:
        target = Path("chrome-profiles") / profile_arg

    target.mkdir(parents=True, exist_ok=True)
    return str(target.resolve())


def run():
    args = parse_args()
    profile_dir = resolve_profile_dir(args.profile)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=args.headless,
            channel="chrome",
            args=["--start-maximized"],
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto(args.url)

        print(f"Using profile directory: {profile_dir}")
        print("Please login if required...")
        page.wait_for_timeout(5000)

        apply_selector = (
            "button:has-text('Apply'), "
            "button:has-text('Apply Now'), "
            "button:has-text('Apply With Autofill')"
        )

        page.wait_for_selector(apply_selector, timeout=0)
        print("Jobs detected. Starting automation...")

        max_links = args.max_links
        saved_count = 0
        attempts = 0
        no_new_job_rounds = 0
        max_no_new_job_rounds = 5
        stuck_on_card = 0  # consecutive no-progress passes on the current top card

        while saved_count < max_links:
            total = page.locator(apply_selector).count()
            print("DEBUG: Apply buttons found:", total)

            if total == 0:
                loaded = try_load_more_jobs(page, apply_selector, total)
                if loaded:
                    no_new_job_rounds = 0
                    continue
                no_new_job_rounds += 1
                if no_new_job_rounds >= max_no_new_job_rounds:
                    print("No more jobs available after multiple scroll attempts.")
                    break
                continue

            no_new_job_rounds = 0
            attempts += 1
            print(f"\nAttempt {attempts} | saved {saved_count}/{max_links} "
                  f"| stuck={stuck_on_card}")

            made_progress = False
            try:
                # Open the job's apply modal (proven 2-step click sequence).
                apply_btn = page.locator(apply_selector).first
                apply_btn.click()
                page.wait_for_timeout(MODAL_SETTLE)

                page_text = page.inner_text("body")
                if any(keyword in page_text for keyword in BLOCK_KEYWORDS):
                    print("Restricted job - skipping")
                    dismiss_modal(page)
                    made_progress = True  # card gets marked, leaves feed
                else:
                    page.locator(apply_selector).first.click(force=True)
                    page.wait_for_timeout(MODAL_SETTLE)

                    job_url = extract_external_url(context, page)
                    page.bring_to_front()

                    if job_url:
                        print("Extracted URL:", job_url)
                        if not is_application_url(job_url):
                            print("Non-application portal - skipping")
                            dismiss_modal(page)
                            made_progress = True
                        elif job_url in saved_links:
                            print("Duplicate job - skipping")
                            dismiss_modal(page)
                            made_progress = True
                        else:
                            saved_links.add(job_url)
                            collected_links.append(job_url)
                            save_to_excel(args.output)
                            saved_count += 1
                            print(f"Saved ({saved_count}/{max_links}):", job_url)
                            dismiss_modal(page)
                            made_progress = True
                    else:
                        print("No external URL detected")
                        dismiss_modal(page)
            except Exception as e:
                print("Iteration error - recovering:", repr(e))
                dismiss_modal(page)

            # Always clean up extra tabs and settle.
            close_extra_tabs(context, page)
            page.wait_for_timeout(400)

            # Stuck-card guard: if the top card never leaves the feed, force past
            # it by scrolling, so we don't reprocess the same job forever.
            if made_progress:
                stuck_on_card = 0
            else:
                stuck_on_card += 1
                if stuck_on_card >= MAX_STUCK_PER_CARD:
                    print("Card stuck - scrolling past it.")
                    page.mouse.wheel(0, 1200)
                    page.wait_for_timeout(800)
                    stuck_on_card = 0

        print("\nExtraction complete.")
        context.close()

    save_to_excel(args.output)


if __name__ == "__main__":
    run()
