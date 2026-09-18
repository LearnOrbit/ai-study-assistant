import unittest
from datetime import datetime, timedelta
from test_workspace_integration import WorkspaceIntegration, app, get_current_user_id
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.problem_attempt import ProblemAttempt, ProblemType
from app.models.solved_problem import SolvedProblem
from app.models.flashcard import Deck, Flashcard, CardReview

class ProgressTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = WorkspaceIntegration.asyncSetUp
    asyncTearDown = WorkspaceIntegration.asyncTearDown

    async def test_periods_streak_and_ungraded_separation(self):
        app.dependency_overrides[get_current_user_id] = lambda: 777
        now = datetime.utcnow()
        async with AsyncSessionLocal() as db:
            db.add(User(id=777, email='progress@example.invalid', username='progress', hashed_password='!disabled'))
            await db.flush()
            deck = Deck(user_id=777, title='Progress'); db.add(deck); await db.flush()
            card = Flashcard(deck_id=deck.id, front='q', back='a'); db.add(card); await db.flush()
            db.add(CardReview(user_id=777, card_id=card.id, rating='again', created_at=now))
            for days in [1, 2, 20]:
                db.add(SolvedProblem(user_id=777, subject='math', problem='q', result={}, created_at=now - timedelta(days=days)))
            for correct in [True, None]:
                db.add(ProblemAttempt(user_id=777, problem_type=ProblemType.MATH, problem_text='q', solution='a', is_correct=correct, created_at=now))
            await db.commit()
        week = (await self.client.get('/api/analytics')).json()
        self.assertEqual(week['accuracy'], 100)
        self.assertEqual(week['graded_attempts'], 1)
        self.assertEqual(week['solutions'], 2)
        self.assertEqual(week['reviews'], 1)
        self.assertEqual(week['review_ratings']['again'], 1)
        self.assertEqual(week['streak'], 3)
        self.assertEqual(week['active_days'], 3)
        self.assertEqual(len(week['daily']), 7)
        self.assertEqual(week['daily'][-1]['total'], 3)
        month = (await self.client.get('/api/analytics?range=month')).json()
        self.assertEqual(month['solutions'], 3)
        self.assertEqual(len(month['daily']), 30)
        semester = (await self.client.get('/api/analytics?range=semester')).json()
        self.assertEqual(len(semester['daily']), 180)
        app.dependency_overrides[get_current_user_id] = lambda: 998
        empty = (await self.client.get('/api/analytics')).json()
        self.assertEqual(empty['streak'], 0)
        self.assertIsNone(empty['accuracy'])
        self.assertEqual(empty['reviews'], 0)
        self.assertEqual(empty['solutions'], 0)
