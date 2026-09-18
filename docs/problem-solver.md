# Problem solver

Open `/solver` to solve typed questions or PNG/JPEG/WebP photos (10 MB maximum),
reveal a hint before the explanation, and reopen or delete saved solutions.

API: `POST /api/problems/solve` accepts `{problem, subject}`; `POST /api/problems/image`
accepts multipart `file` and `subject`. Both return a saved solution with `id`,
`problem`, `subject`, `hint`, `steps`, `answer`, `verification`, and `created_at`.
`GET /api/problems/history?offset=0&limit=20` lists the current user's solutions;
`DELETE /api/problems/{id}` removes one. AI JSON is validated before saving.
The additive `solved_problems` table is created at backend startup.

Requires a valid backend `GEMINI_API_KEY`. AI explanations can be wrong and are
not treated as graded practice attempts. Existing shared-demo authentication
still applies; see workspace-setup.md before public hosting.

Run backend checks: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m unittest discover -s tests -p 'test_solver.py'`.
