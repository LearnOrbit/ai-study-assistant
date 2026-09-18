# Progress analytics

`GET /api/analytics?range=week|month|semester` includes practice, saved solutions,
flashcard review events, and uploads for 7, 30, or 180 UTC calendar days.
The web `/analytics` page displays the same data.

Accuracy uses only attempts with a non-null correctness value. AI solutions and
self-reported flashcard recall are counted separately, never as correct answers.
`daily` contains every date in the selected range (zero-filled); `count` remains
practice attempts for compatibility, while `total` combines all activity types.

`streak` counts consecutive active UTC dates ending today or yesterday, independent
of the selected range. `active_days` is restricted to the range. `review_ratings`
contains again/hard/good/easy counts. No AI is needed to calculate these metrics.
Deleting a solution or deck removes its associated activity from calculations.

The API uses the existing user dependency; shared-demo authentication is still the
local default. No private multi-user deployment is claimed.

Test: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m unittest discover -s tests -p 'test_progress.py'`
from backend. Checks cover date ranges, zero-filled days, ownership, ungraded
attempts, distinct activity counts, and streaks.
