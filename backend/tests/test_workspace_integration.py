"""Integration checks using an isolated database and deterministic AI responses.
Run from backend: PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m unittest discover -s tests -p 'test_workspace_integration.py'
"""
import io
import os
import tempfile
import unittest
from unittest.mock import patch

sandbox = tempfile.TemporaryDirectory(prefix="studyspace-tests-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{sandbox.name}/test.db"
os.environ["UPLOAD_DIR"] = f"{sandbox.name}/uploads"
os.environ["GEMINI_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["GROQ_API_KEY"] = ""

from httpx import ASGITransport, AsyncClient
from PIL import Image
from app.main import app
from app.core.security import get_current_user_id
from app.services.ai_engine.llm_client import get_llm_client

class FakeAI:
    async def generate_completion(self, messages, **kwargs):
        return "A concise summary of photosynthesis."
    async def generate_summary(self, text):
        return text
    async def generate_content(self, contents, **kwargs):
        assert isinstance(contents[1]["data"], bytes)
        assert contents[1]["data"]
        return "Processed the actual uploaded bytes."

class WorkspaceIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.lifespan = app.router.lifespan_context(app)
        await self.lifespan.__aenter__()
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        app.dependency_overrides[get_llm_client] = lambda: FakeAI()

    async def asyncTearDown(self):
        app.dependency_overrides.clear()
        await self.client.aclose()
        await self.lifespan.__aexit__(None, None, None)

    async def upload(self, filename="notes.txt", data=b"Photosynthesis uses sunlight. Plants use carbon dioxide."):
        response = await self.client.post("/api/documents/upload", files={"file": (filename, data, "text/plain")})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def test_library_persistence_search_summary_and_delete(self):
        doc = await self.upload()
        self.assertEqual(doc["processing_status"], "completed")
        listed = (await self.client.get("/api/documents/")).json()
        self.assertIn(doc["id"], [item["id"] for item in listed])
        found = (await self.client.get(f'/api/documents/{doc["id"]}/search', params={"q": "sunlight"})).json()
        self.assertIn("sunlight", found["results"][0]["excerpt"])
        missing = (await self.client.get(f'/api/documents/{doc["id"]}/search', params={"q": "unmatched"})).json()
        self.assertEqual(missing["results"], [])
        summary = await self.client.post(f'/api/summarize/{doc["id"]}', json={"level": "moderate"})
        self.assertEqual(summary.status_code, 200, summary.text)
        self.assertIn("photosynthesis", summary.json()["summary"])
        self.assertEqual((await self.client.delete(f'/api/documents/{doc["id"]}')).status_code, 204)
        self.assertEqual((await self.client.get(f'/api/documents/{doc["id"]}')).status_code, 404)

    async def test_owner_isolation(self):
        doc = await self.upload()
        app.dependency_overrides[get_current_user_id] = lambda: 999
        for path in [f'/api/documents/{doc["id"]}', f'/api/documents/{doc["id"]}/search?q=sunlight']:
            self.assertEqual((await self.client.get(path)).status_code, 404)
        self.assertEqual((await self.client.post(f'/api/summarize/{doc["id"]}', json={})).status_code, 404)
        self.assertEqual((await self.client.get('/api/documents/')).json(), [])

    async def test_upload_validation(self):
        for name, data in [("bad.doc", b"unsupported"), ("empty.txt", b""), ("large.txt", b"x" * (10 * 1024 * 1024 + 1))]:
            result = await self.client.post('/api/documents/upload', files={"file": (name, data)})
            self.assertEqual(result.status_code, 400, result.text)

    async def test_docx_extraction(self):
        from docx import Document
        document = Document()
        document.add_paragraph("Cell biology lecture notes.")
        data = io.BytesIO()
        document.save(data)
        doc = await self.upload("lecture.docx", data.getvalue())
        self.assertEqual(doc["processing_status"], "completed")
        self.assertIn("Cell biology", doc["extracted_text"])

    async def test_named_tools_receive_uploads_instead_of_document_id_errors(self):
        data = io.BytesIO()
        Image.new("RGB", (2, 2)).save(data, format="PNG")
        image = await self.client.post('/api/summarize/image', files={"file": ("diagram.png", data.getvalue(), "image/png")})
        self.assertEqual(image.status_code, 200, image.text)
        audio = await self.client.post('/api/summarize/audio', files={"file": ("recording.webm", b"audio-test-data", "audio/webm;codecs=opus")})
        self.assertEqual(audio.status_code, 200, audio.text)
        invalid = await self.client.post('/api/summarize/image', files={"file": ("bad.png", b"not an image", "image/png")})
        self.assertEqual(invalid.status_code, 400)

    async def test_text_and_problem_validation(self):
        self.assertEqual((await self.client.post('/api/summarize/text', json={"text": " "})).status_code, 400)
        self.assertEqual((await self.client.post('/api/summarize/solve', json={"problem": " "})).status_code, 400)
        self.assertEqual((await self.client.post('/api/summarize/text', json={"text": "Photosynthesis uses light."})).status_code, 200)
        self.assertEqual((await self.client.post('/api/summarize/solve', json={"problem": "2x = 8"})).status_code, 200)

    async def test_missing_ai_key_is_an_error_not_a_successful_answer(self):
        app.dependency_overrides.pop(get_llm_client)
        result = await self.client.post('/api/summarize/text', json={"text": "Study material"})
        self.assertEqual(result.status_code, 503)
        self.assertEqual((await self.client.post('/api/chat/', json={"query": "Explain photosynthesis"})).status_code, 503)

    async def test_practice_scoring_and_persistent_analytics(self):
        before = (await self.client.get('/api/analytics')).json()
        questions = (await self.client.get('/api/practice/math')).json()["questions"]
        self.assertEqual(len({q["id"] for q in questions}), 3)
        self.assertNotIn("answer", questions[0])
        correct = await self.client.post('/api/practice/attempts', json={"question_id": questions[0]["id"], "option": 0})
        self.assertTrue(correct.json()["correct"])
        wrong = await self.client.post('/api/practice/attempts', json={"question_id": questions[1]["id"], "option": 0})
        self.assertFalse(wrong.json()["correct"])
        after = (await self.client.get('/api/analytics')).json()
        self.assertEqual(after["attempts"], before["attempts"] + 2)
        self.assertEqual(after["correct"], before["correct"] + 1)
        self.assertEqual(after["daily"][-1]["count"], before["daily"][-1]["count"] + 2)
        self.assertEqual((await self.client.get('/api/analytics?range=invalid')).status_code, 422)
        self.assertEqual((await self.client.post('/api/practice/attempts', json={"question_id": "math--1", "option": 0})).status_code, 404)

    async def test_cors_accepts_alternate_local_frontend_port(self):
        response = await self.client.options('/api/chat/', headers={"Origin": "http://localhost:5174", "Access-Control-Request-Method": "POST"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['access-control-allow-origin'], 'http://localhost:5174')

    async def test_provider_errors_are_safe_and_actionable(self):
        from app.services.ai_engine.llm_client import LLMClient
        from app.config import settings
        from google.api_core.exceptions import InvalidArgument, ResourceExhausted
        from fastapi import HTTPException
        with patch.object(settings, 'gemini_api_key', 'test-only-key'):
            client = LLMClient()
            for provider_error, expected_status in [(InvalidArgument('invalid key'), 503), (ResourceExhausted('quota'), 429)]:
                with patch('app.services.ai_engine.llm_client.genai.GenerativeModel') as model:
                    model.return_value.generate_content.side_effect = provider_error
                    with self.assertRaises(HTTPException) as caught:
                        await client.generate_response('Explain photosynthesis')
                    self.assertEqual(caught.exception.status_code, expected_status)
                    self.assertNotIn('test-only-key', caught.exception.detail)

    async def test_chat_preserves_rejection_and_service_failure_distinction(self):
        from app.config import settings
        with patch.object(settings, 'gemini_api_key', 'test-only-key'), patch('app.api.chat_routes.get_validator') as validator:
            validator.return_value.process_query.return_value = {'success': False, 'message': 'Ask a study question.', 'validation': {'valid': False}}
            rejection = await self.client.post('/api/chat/', json={'query': 'hello'})
            self.assertEqual(rejection.status_code, 200)
            self.assertFalse(rejection.json()['validation']['valid'])
            validator.return_value.process_query.return_value = {'success': False, 'message': 'Provider failed'}
            failure = await self.client.post('/api/chat/', json={'query': 'Explain photosynthesis'})
            self.assertEqual(failure.status_code, 502)
            validator.return_value.process_query.return_value = {'success': True, 'response': 'Plants convert light into chemical energy.'}
            success = await self.client.post('/api/chat/', json={'query': 'Explain photosynthesis'})
            self.assertEqual(success.status_code, 200)
            self.assertTrue(success.json()['success'])

    async def test_date_filters_exclude_older_attempts(self):
        from app.core.database import AsyncSessionLocal
        from app.models.problem_attempt import ProblemAttempt, ProblemType
        from datetime import datetime, timedelta
        app.dependency_overrides[get_current_user_id] = lambda: 888
        async with AsyncSessionLocal() as db:
            from app.models.user import User
            db.add(User(id=888, email='date-test@example.invalid', username='date-test', hashed_password='!disabled'))
            await db.flush()
            db.add(ProblemAttempt(user_id=888, problem_type=ProblemType.MATH, problem_text='Historical test', solution='Example', is_correct=True, created_at=datetime.utcnow() - timedelta(days=15)))
            await db.commit()
        week = (await self.client.get('/api/analytics?range=week')).json()
        month = (await self.client.get('/api/analytics?range=month')).json()
        self.assertEqual(week['attempts'], 0)
        self.assertEqual(month['attempts'], 1)
        self.assertEqual(month['accuracy'], 100)

if __name__ == '__main__':
    unittest.main()
