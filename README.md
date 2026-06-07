---
title: Jobright Link Extractor
emoji: 🔎
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 8000
pinned: false
---

# Jobright Job Application Link Extractor (Playwright)

Automates job application workflows on Jobright.ai using Playwright and Chrome, extracts non-portal job application links, and saves them to an Excel sheet.

## Features

* Works with any Chrome profile (`--profile`)
* Reuses login session with persistent browser data
* Clicks: Apply, Apply Now, Apply With Autofill
* Prefers manual apply paths when available
* Skips restricted jobs (Security Clearance / U.S. Citizen Only)
* Filters out known job portals
* Saves unique external application links to Excel
* Handles infinite scrolling and popup/same-tab flows

## Requirements

* Python 3.9+
* Google Chrome installed

## Complete Setup (Windows)

### 1. Create and activate virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
playwright install
```

### 3. Run with a profile name

```powershell
python extracted_job.py --profile anil
```

This creates and uses `./chrome-profiles/anil` automatically.

### 4. First run login

* Browser opens on Jobright
* Login once manually
* Future runs with same `--profile` reuse session

## Usage

```powershell
python extracted_job.py --profile <name-or-path> --max-links 30 --output filtered_job_links.xlsx
```

### Common examples

```powershell
# Default local profile (./chrome-profiles/default)
python extracted_job.py

# Named local profile
python extracted_job.py --profile recruiter1

# Absolute profile path
python extracted_job.py --profile "C:\Users\You\Desktop\my-chrome-profile"

# Save up to 50 links in custom file
python extracted_job.py --profile recruiter1 --max-links 50 --output links.xlsx
```

## Output

* Excel file (default: `filtered_job_links.xlsx`)
* Unique filtered job URLs

## Notes

* Keep browser open while script runs
* If Jobright UI text changes, selectors may need updates
* External form filling is intentionally manual
