import io
import json
import unittest
from test_workspace_integration import WorkspaceIntegration, app, get_llm_client, get_current_user_id
from PIL import Image

SOLUTION = {'problem': '2x + 5 = 13', 'hint': 'Subtract five.', 'steps': ['2x = 8', 'x = 4'], 'answer': '4', 'verification': '2 × 4 + 5 = 13'}

class SolverAI:
    async def generate_response(self, prompt, **kwargs):
        return json.dumps(SOLUTION)
    async def generate_content(self, contents, **kwargs):
        assert isinstance(contents[1]['data'], bytes)
        return json.dumps(SOLUTION)

class SolverTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = WorkspaceIntegration.asyncSetUp
    asyncTearDown = WorkspaceIntegration.asyncTearDown

    async def test_saved_solution_is_not_practice_accuracy_and_is_owner_scoped(self):
        app.dependency_overrides[get_llm_client] = SolverAI
        before = (await self.client.get('/api/analytics')).json()['attempts']
        response = await self.client.post('/api/problems/solve', json={'problem': '2x + 5 = 13'})
        self.assertEqual(response.status_code, 201, response.text)
        row = response.json()
        self.assertEqual(row['answer'], '4')
        self.assertIn(row['id'], [x['id'] for x in (await self.client.get('/api/problems/history')).json()])
        self.assertEqual((await self.client.get('/api/analytics')).json()['attempts'], before)
        app.dependency_overrides[get_current_user_id] = lambda: 999
        self.assertEqual((await self.client.get('/api/problems/history')).json(), [])
        self.assertEqual((await self.client.delete(f"/api/problems/{row['id']}")).status_code, 404)
        app.dependency_overrides.pop(get_current_user_id)
        self.assertEqual((await self.client.delete(f"/api/problems/{row['id']}")).status_code, 204)

    async def test_invalid_ai_output_is_not_saved(self):
        class InvalidAI:
            async def generate_response(self, *args, **kwargs): return '{"answer": "invented"}'
        app.dependency_overrides[get_llm_client] = InvalidAI
        before = (await self.client.get('/api/problems/history')).json()
        response = await self.client.post('/api/problems/solve', json={'problem': '2x = 8'})
        self.assertEqual(response.status_code, 502)
        self.assertEqual((await self.client.get('/api/problems/history')).json(), before)
        self.assertEqual((await self.client.post('/api/problems/solve', json={'problem': '  '})).status_code, 400)
        self.assertEqual((await self.client.get('/api/problems/history?limit=101')).status_code, 422)

    async def test_photo_input_validation(self):
        app.dependency_overrides[get_llm_client] = SolverAI
        data = io.BytesIO(); Image.new('RGB', (2, 2)).save(data, format='PNG')
        good = await self.client.post('/api/problems/image', files={'file': ('q.png', data.getvalue(), 'image/png')})
        self.assertEqual(good.status_code, 201, good.text)
        bad = await self.client.post('/api/problems/image', files={'file': ('q.png', b'bad', 'image/png')})
        self.assertEqual(bad.status_code, 400)
