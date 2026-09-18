import json
import unittest
from test_workspace_integration import WorkspaceIntegration, app, get_llm_client, get_current_user_id

class CardsAI:
    async def generate_response(self, prompt, **kwargs):
        return json.dumps({'cards': [{'front': f'Question {i}', 'back': f'Answer {i}'} for i in range(3)]})

class FlashcardTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = WorkspaceIntegration.asyncSetUp
    asyncTearDown = WorkspaceIntegration.asyncTearDown

    async def create(self, **extra):
        app.dependency_overrides[get_llm_client] = CardsAI
        body = {'title': 'Biology', 'text': 'Cells have membranes.', 'count': 3, **extra}
        response = await self.client.post('/api/flashcards/decks', json=body)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def test_generate_edit_review_reload_and_delete(self):
        deck = await self.create()
        card = deck['cards'][0]
        response = await self.client.patch(f"/api/flashcards/cards/{card['id']}", json={'front': 'Edited question', 'back': 'Edited answer', 'version': card['version']})
        self.assertEqual(response.status_code, 200, response.text)
        card = response.json()
        review = {'rating': 'good', 'version': card['version']}
        first = await self.client.post(f"/api/flashcards/cards/{card['id']}/review", json=review)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()['interval_days'], 1)
        duplicate = await self.client.post(f"/api/flashcards/cards/{card['id']}/review", json=review)
        self.assertEqual(duplicate.status_code, 409)
        saved = (await self.client.get(f"/api/flashcards/decks/{deck['id']}")).json()
        self.assertEqual(saved['cards'][0]['front'], 'Edited question')
        self.assertEqual(saved['cards'][0]['version'], 2)
        listed = (await self.client.get('/api/flashcards/decks')).json()
        self.assertEqual(next(d['due'] for d in listed if d['id'] == deck['id']), 2)
        self.assertEqual((await self.client.delete(f"/api/flashcards/decks/{deck['id']}")).status_code, 204)
        self.assertEqual((await self.client.get(f"/api/flashcards/decks/{deck['id']}")).status_code, 404)

    async def test_owner_and_document_source(self):
        doc = await WorkspaceIntegration.upload(self)
        deck = await self.create(text=None, document_id=doc['id'])
        card = deck['cards'][0]
        app.dependency_overrides[get_current_user_id] = lambda: 999
        self.assertEqual((await self.client.get('/api/flashcards/decks')).json(), [])
        self.assertEqual((await self.client.get(f"/api/flashcards/decks/{deck['id']}")).status_code, 404)
        self.assertEqual((await self.client.post(f"/api/flashcards/cards/{card['id']}/review", json={'rating': 'easy', 'version': 0})).status_code, 404)
        self.assertEqual((await self.client.patch(f"/api/flashcards/cards/{card['id']}", json={'front': 'a', 'back': 'b', 'version': 0})).status_code, 404)
        self.assertEqual((await self.client.post('/api/flashcards/decks', json={'title': 'x', 'document_id': doc['id'], 'count': 3})).status_code, 404)

    async def test_invalid_generation_and_validation(self):
        class BadAI:
            async def generate_response(self, *args, **kwargs):
                return json.dumps({'cards': [{'front': 'duplicate', 'back': 'a'}] * 3})
        app.dependency_overrides[get_llm_client] = BadAI
        before = (await self.client.get('/api/flashcards/decks')).json()
        self.assertEqual((await self.client.post('/api/flashcards/decks', json={'title': 'x', 'text': 'notes', 'count': 3})).status_code, 502)
        self.assertEqual((await self.client.get('/api/flashcards/decks')).json(), before)
        for body in [{'title': 'x', 'text': ' '}, {'title': ' ', 'text': 'notes'}, {'title': 'x', 'text': 'notes', 'document_id': 1}, {'title': 'x', 'text': 'notes', 'count': 100}]:
            self.assertEqual((await self.client.post('/api/flashcards/decks', json=body)).status_code, 422)
