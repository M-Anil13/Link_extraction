# Jobright Extractor — Frontend

React + Vite + Tailwind UI for the link extractor. Streams live progress over a
WebSocket and shows extracted links in a table.

## Run

```bash
# 1. Backend (from repo root)
uvicorn app.main:app --reload --port 8000

# 2. Frontend (this folder)
npm install
npm run dev      # http://localhost:5173
```

Open the UI, set the Chrome profile + max links, click **Start**. Links stream
in live; click **Download Excel** to grab `filtered_job_links.xlsx`.

## Notes

- Backend URL is hardcoded to `localhost:8000` in `src/App.jsx` (`API` / `WS_URL`).
- `Headless` on reuses the saved Chrome profile session. If Jobright login has
  expired, run the CLI once non-headless to log in:
  `python extracted_job.py --profile <name>`.
