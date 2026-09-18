# Flashcards

Open `/flashcards` to generate 3–20 cards from pasted notes or a completed library
document. Review the AI output, edit questions/answers, reveal an answer, and rate
recall. This is a simple interval scheduler, not a claim of scientifically measured mastery.

- Again: 10 minutes; Hard: at least 1 day; Good: at least 1 day, then double;
  Easy: at least 4 days, then triple the prior interval.
- Review/edit requests include the card version. Stale writes return 409; reopen
  the deck to refresh. Future cards cannot be reviewed early.
- Decks, cards, and review events persist in three additive tables created on startup.
- Deleting a deck also deletes its cards and reviews, including their analytics.
- All queries use the authenticated user dependency (currently shared-demo mode).

Endpoints under `/api/flashcards`: POST/GET `/decks`, GET/DELETE `/decks/{id}`,
PATCH `/cards/{id}`, POST `/cards/{id}/review`. Generation accepts `title`, `count`,
and exactly one of `text` or `document_id`. Edit accepts `front`, `back`, `version`;
review accepts `rating` (`again`, `hard`, `good`, `easy`) and `version`.
AI output must match the requested card count and contain unique, nonempty questions.

Run `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m unittest discover -s tests -p 'test_flashcards.py'`
from backend. Live generation additionally needs a valid server-side Gemini key.
