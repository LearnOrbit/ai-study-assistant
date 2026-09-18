"""Study tools with validated inputs and genuine provider responses."""
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image, UnidentifiedImageError
from app.config import settings
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.document import Document, ProcessingStatus
from app.schemas.summary import SummaryRequest, SummaryResponse
from app.services.ai_engine.llm_client import LLMClient, get_llm_client
from app.services.ai_engine.prompts import build_summary_prompt, SYSTEM_PROMPT

router = APIRouter()

class ProblemRequest(BaseModel):
    problem: str = Field(..., min_length=1, max_length=20000)
    type: str = Field(default="doubt", max_length=50)

class TextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100000)

async def summarize(text, llm, level="moderate", focus=None):
    if not text.strip():
        raise HTTPException(400, "Enter some text to summarize.")
    if len(text) > settings.max_text_length:
        raise HTTPException(413, "This document is too long to summarize. Split it into smaller documents.")
    # The configured Gemini model accepts the full bounded document in one request.
    prompt = build_summary_prompt(text, level)
    if focus:
        prompt += "\nFocus on: " + ", ".join(focus)
    return await llm.generate_completion([
        {"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt},
    ], max_tokens=3000)

@router.post("/text")
async def summarize_text(request: TextRequest, llm: LLMClient = Depends(get_llm_client)):
    summary = await summarize(request.text, llm)
    return {"summary": summary, "word_count": len(summary.split())}

@router.post("/solve")
async def solve_problem(request: ProblemRequest, llm: LLMClient = Depends(get_llm_client)):
    if not request.problem.strip():
        raise HTTPException(400, "Enter a problem or concept.")
    solution = await llm.generate_completion([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Explain this {request.type} study problem. Show steps, verify the answer, and explain common mistakes.\n\n{request.problem}"},
    ], max_tokens=3000)
    return {"solution": solution, "problem": request.problem}

async def read_upload(file):
    contents = await file.read(settings.max_file_size + 1)
    if not contents:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(contents) > settings.max_file_size:
        raise HTTPException(413, "Maximum upload size is 10 MB.")
    return contents

@router.post("/image")
async def analyze_image(file: UploadFile = File(...), llm: LLMClient = Depends(get_llm_client)):
    contents = await read_upload(file)
    try:
        with Image.open(io.BytesIO(contents)) as image:
            image.verify()
            mime = Image.MIME.get(image.format)
        if mime not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(400, "Choose a PNG, JPEG, or WebP image.")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(400, "The file is not a valid image.")
    analysis = await llm.generate_content([
        "Analyze this study image. Transcribe relevant text, explain diagrams, and solve any problems step by step.",
        {"mime_type": mime, "data": contents},
    ], max_tokens=3000)
    return {"analysis": analysis, "filename": file.filename}

@router.post("/audio")
async def transcribe_audio(file: UploadFile = File(...), llm: LLMClient = Depends(get_llm_client)):
    contents = await read_upload(file)
    mime = (file.content_type or "").split(";")[0].lower()
    aliases = {"audio/x-m4a": "audio/mp4", "audio/m4a": "audio/mp4", "audio/mp3": "audio/mpeg", "audio/x-wav": "audio/wav"}
    mime = aliases.get(mime, mime)
    if mime not in {"audio/mpeg", "audio/mp4", "audio/wav", "audio/webm", "audio/ogg", "audio/flac"}:
        raise HTTPException(400, "Unsupported audio format. Use MP3, M4A, WAV, WebM, OGG, or FLAC.")
    transcription = await llm.generate_content([
        "Transcribe the speech in this recording faithfully, then summarize its key study points. Do not invent inaudible speech.",
        {"mime_type": mime, "data": contents},
    ], max_tokens=4000)
    return {"transcription": transcription, "filename": file.filename}

async def owned_document(document_id, user_id, db):
    document = await db.scalar(select(Document).where(Document.id == document_id, Document.user_id == user_id))
    if document is None:
        raise HTTPException(404, "Document not found")
    if document.processing_status != ProcessingStatus.COMPLETED or not document.extracted_text:
        raise HTTPException(409, "Document text is unavailable. Check its processing status in your library.")
    return document

# Integer path converters prevent named tools from matching document routes.
@router.post("/{document_id:int}", response_model=SummaryResponse)
async def generate_summary(document_id: int, summary_request: SummaryRequest,
                           user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db),
                           llm: LLMClient = Depends(get_llm_client)):
    document = await owned_document(document_id, user_id, db)
    summary = await summarize(document.extracted_text, llm, summary_request.level.value, summary_request.focus_areas)
    document.summary_count += 1
    await db.commit()
    return SummaryResponse(document_id=document_id, summary=summary, level=summary_request.level,
                           word_count=len(summary.split()), original_length=len(document.extracted_text))

@router.post("/{document_id:int}/key-points")
async def extract_key_points(document_id: int, user_id: int = Depends(get_current_user_id),
                             db: AsyncSession = Depends(get_db), llm: LLMClient = Depends(get_llm_client)):
    document = await owned_document(document_id, user_id, db)
    points = await summarize(document.extracted_text, llm, "brief", ["key concepts, definitions, and formulas"])
    return {"document_id": document_id, "key_points": points}
