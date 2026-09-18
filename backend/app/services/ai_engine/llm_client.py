"""Shared Gemini client for text and uploaded study material."""
import asyncio
import logging
from fastapi import HTTPException
from google.api_core.exceptions import InvalidArgument, PermissionDenied, ResourceExhausted, NotFound
import google.generativeai as genai
from app.config import settings

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.api_key = settings.gemini_api_key
        if self.api_key:
            genai.configure(api_key=self.api_key)

    async def generate_content(self, contents, temperature=0.5, max_tokens=2000):
        if not self.api_key:
            raise HTTPException(503, "Study AI is not configured. Set GEMINI_API_KEY on the backend.")
        try:
            model = genai.GenerativeModel(settings.gemini_model)
            response = await asyncio.wait_for(asyncio.to_thread(
                model.generate_content, contents,
                generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
            ), timeout=90)
            if not response.text.strip():
                raise ValueError("Empty AI response")
            return response.text
        except (InvalidArgument, PermissionDenied) as error:
            logger.warning("AI configuration rejected (%s)", type(error).__name__)
            raise HTTPException(503, "The AI provider rejected the request. Check the backend GEMINI_API_KEY and supported input format.") from error
        except ResourceExhausted as error:
            raise HTTPException(429, "The AI usage limit was reached. Please try again later.") from error
        except NotFound as error:
            raise HTTPException(503, "The configured AI model is unavailable. Check GEMINI_MODEL on the backend.") from error
        except Exception as error:
            logger.warning("AI generation failed (%s)", type(error).__name__)
            raise HTTPException(502, "The AI service is unavailable. Try again or check the backend API key and GEMINI_MODEL.") from error

    async def generate_response(self, prompt, max_tokens=1000):
        return await self.generate_content(prompt, max_tokens=max_tokens)

    async def generate_summary(self, text):
        return await self.generate_response(f"Summarize this study material accurately:\n\n{text}")

    async def generate_completion(self, messages, temperature=0.7, max_tokens=2000):
        prompt = "\n\n".join(f"{item['role']}: {item['content']}" for item in messages)
        return await self.generate_content(prompt, temperature, max_tokens)


def get_llm_client():
    return LLMClient()
