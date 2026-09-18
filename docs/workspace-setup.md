# Running the connected study workspace

The browser uses `/api` by default. Vite forwards requests to `http://127.0.0.1:8000`,
so it works even if Vite selects port 5174 or 5175. Run from the repository root:

```sh
cd backend
venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```sh
cd frontend
npm run dev
```

Set these values in `backend/.env` (one KEY=value assignment per line):

```dotenv
GEMINI_API_KEY=your-valid-key
GEMINI_MODEL=gemini-2.5-flash
DATABASE_URL=sqlite+aiosqlite:///./ai_study.db
```

Restart the backend after changing `.env`. The key stays on the backend; never put
it in a `VITE_` variable. Text, image, audio, and chat generation require a valid
Gemini key. Library upload/search/delete and curated practice work without one.
An invalid key or unavailable model produces an error rather than a fabricated result.
The model name is configurable; consult Google's model availability for your account.

## Data behavior

- Uploads are persisted immediately. PDF, DOCX and UTF-8 TXT are supported, up to 10 MB.
- Documents survive refresh. Extraction failures stay visible in the library and can be removed.
- Search returns actual text matches; an empty result means no matches.
- Summaries process all text, subject to the configured `MAX_TEXT_LENGTH` limit.
- Practice has three curated introductory exercises per subject. Checking an answer
  records an attempt; repeating a set records new attempts.
- Analytics reads persisted attempts and uploads. Date filters use UTC calendar days.
  There are no estimated study hours, fictional streaks, or randomly generated charts.
- The existing authentication configuration is a local shared demo (`TESTING_MODE`
  in `backend/app/core/security.py`, user 1). It is not private multi-user hosting.
  Do not expose this demo backend publicly without completing authentication.

## Hosting

For a frontend on a different host, set `VITE_API_BASE_URL` to the backend's public
HTTPS URL plus `/api` **before building**. Set `CORS_ORIGINS` in the backend to a JSON
array containing the frontend's exact origin. The Vite proxy only exists during
development; a deployed static frontend does not run Python. The root `vercel.json` builds `frontend/dist` and supplies SPA rewrites for the
four tool pages. Use the repository root as the Vercel Root Directory. Other hosts
need equivalent SPA fallbacks for direct page visits.

## Verification

```sh
cd backend
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m unittest discover -s tests -p 'test_workspace_integration.py'
cd ../frontend
npm run build
```

The tests use a temporary database, generated documents, and a fake AI provider.
They do not read or alter your study records and do not incur provider usage.
Live AI responses must also be checked with a working key.
