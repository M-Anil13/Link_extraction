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
    "careerbuilder.com"
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
    page.wait_for_timeout(1600)

    new_total = page.locator(apply_selector).count()
    print(f"DEBUG: jobs before scroll={previous_total}, after scroll={new_total}")
    return new_total > previous_total


def click_yes_applied_fast(page):
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
        processed = 0
        no_new_job_rounds = 0
        max_no_new_job_rounds = 5

        while processed < max_links:
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
            print(f"\nProcessing saved-job target {processed + 1}")

            try:
                apply_btn = page.locator(apply_selector).first
                apply_btn.click()
                page.wait_for_timeout(900)
            except Exception:
                print("Top Apply button detached from DOM - retrying")
                page.wait_for_timeout(500)
                continue

            page_text = page.inner_text("body")
            if any(keyword in page_text for keyword in BLOCK_KEYWORDS):
                print("Restricted job - skipping")
                page.keyboard.press("Escape")
                page.wait_for_timeout(600)
                continue

            try:
                page.locator(apply_selector).first.click(force=True)
                page.wait_for_timeout(700)
            except Exception:
                print("Apply click failed - skipping")
                page.keyboard.press("Escape")
                continue

            job_url = None
            manual_apply_button = page.locator(
                "button:has-text('No, Apply Manually'), "
                "button:has-text('Apply Manually'), "
                "button:has-text('Apply Without Customizing')"
            )

            try:
                manual_apply_button.first.wait_for(timeout=1000)
                with context.expect_page() as new_page_info:
                    manual_apply_button.first.click(force=True)
                new_page = new_page_info.value
                new_page.wait_for_load_state()
                job_url = new_page.url
                print("Extracted URL:", job_url)
            except Exception:
                print("Manual popup not found")
                if len(context.pages) > 1:
                    new_page = context.pages[-1]
                    new_page.wait_for_load_state()
                    job_url = new_page.url
                elif "jobright.ai" not in page.url:
                    job_url = page.url

            page.bring_to_front()

            if job_url:
                if not is_application_url(job_url):
                    print("Non-application portal detected - skipping")
                    clicked = click_yes_applied_fast(page)
                    if not clicked:
                        page.keyboard.press("Escape")
                else:
                    if job_url not in saved_links:
                        print("Saved job URL:", job_url)
                        saved_links.add(job_url)
                        collected_links.append(job_url)
                        save_to_excel(args.output)
                        processed += 1
                    else:
                        print("Duplicate job detected - skipping")
                        clicked = click_yes_applied_fast(page)
                        if not clicked:
                            page.keyboard.press("Escape")
                        continue

                    clicked = click_yes_applied_fast(page)
                    if not clicked:
                        print("Apply confirmation button not found")
            else:
                print("No job URL detected")
                page.keyboard.press("Escape")
            page.wait_for_timeout(900)

        print("\nExtraction complete.")
        context.close()

    save_to_excel(args.output)


if __name__ == "__main__":
    run()
