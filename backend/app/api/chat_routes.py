# app/api/chat_routes.py

from fastapi import APIRouter, HTTPException, status
from starlette.concurrency import run_in_threadpool
from app.config import settings
from pydantic import BaseModel, Field
from typing import Optional
from app.services.query_validator import get_validator
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    query: str = Field(..., min_length=1, max_length=2000, description="User's study question")
    context: Optional[str] = Field(None, description="Optional conversation context")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Explain Newton's first law of motion",
                "context": "We're studying physics chapter 3"
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    success: bool
    message: Optional[str] = None
    response: Optional[str] = None
    details: Optional[str] = None
    validation: Optional[dict] = None


class ValidationResponse(BaseModel):
    """Response model for validation endpoint"""
    query: str
    valid: bool
    reason: str
    method: str
    details: dict


@router.post("/", response_model=ChatResponse, status_code=200)
async def chat_with_ai(request: ChatRequest):
    """
    Process a study-related query with validation.
    Only study/education-related questions are processed.
    """
    try:
        if not settings.gemini_api_key:
            raise HTTPException(503, "Study AI is not configured. Set GEMINI_API_KEY on the backend.")
        validator = get_validator(use_ai_validation=settings.enable_ai_validation, strict_mode=settings.strict_validation_mode)
        result = await run_in_threadpool(validator.process_query, query=request.query, context=request.context)
        if not result["success"] and not result.get("validation"):
            raise HTTPException(502, "The AI service could not answer. Please try again or check the backend model configuration.")
        
        if result['success']:
            return ChatResponse(
                success=True,
                response=result['response'],
                validation=result.get('validation')
            )
        else:
            return ChatResponse(
                success=False,
                message=result['message'],
                details=result.get('details'),
                validation=result.get('validation')
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request"
        )


@router.post("/validate", response_model=ValidationResponse, status_code=200)
async def validate_query(request: ChatRequest):
    """Validate if a query is study-related without processing it."""
    try:
        validator = get_validator()
        validation = await run_in_threadpool(validator.validate_query, request.query)
        
        return ValidationResponse(
            query=request.query,
            valid=validation['valid'],
            reason=validation['reason'],
            method=validation['method'],
            details=validation
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during validation"
        )


@router.get("/health", status_code=200)
async def health_check():
    """Check if the chat service and validator are working."""
    try:
        validator = get_validator()
        return {
            "status": "healthy",
            "service": "chat_with_validation",
            "validator_configured": True,
            "ai_validation_enabled": validator.use_ai_validation,
            "strict_mode": validator.strict_mode
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {"status": "unhealthy", "error": str(e)}
