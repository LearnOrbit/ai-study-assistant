from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
import os
import uuid
import shutil
from pathlib import Path
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.document import Document, DocumentType, ProcessingStatus
from app.models.user import User
from app.schemas.document import DocumentResponse, DocumentListResponse
from app.config import settings
from app.utils.file_handlers import get_file_type, validate_file
from app.services.document_processing.pdf_processor import process_pdf
from app.services.document_processing.docx_processor import process_docx
from app.services.document_processing.audio_processor import process_audio
from app.services.document_processing.image_processor import process_image, solve_problem_from_image

router = APIRouter()

UPLOAD_DIR = settings.upload_dir

def ensure_upload_dir():
    """Create upload directory if it doesn't exist."""
    Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    subject: Optional[str] = Form(None),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a document for processing

    - **file**: Document file (PDF, DOCX, TXT, Audio, Image, etc.)
    - **title**: Optional custom title (defaults to filename)
    - **subject**: Optional subject classification
    """
    # Read file content to get size for validation
    content = await file.read(settings.max_file_size + 1)
    file_size = len(content)
    
    # Reset file pointer to beginning
    await file.seek(0)
    
    # Validate file with filename and size
    try:
        validate_file(file.filename, file_size)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Determine document type
    extension = Path(file.filename or "").suffix.lower()
    types = {".pdf": DocumentType.PDF, ".docx": DocumentType.DOCX, ".txt": DocumentType.TXT}
    if extension not in types:
        raise HTTPException(400, "Supported library formats are PDF, DOCX, and TXT.")
    if not content:
        raise HTTPException(400, "The document is empty.")
    doc_type = types[extension]

    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"

    # Save file manually (since save_upload_file has different signature)
    try:
        ensure_upload_dir()
        
        # Create user-specific directory
        user_dir = Path(UPLOAD_DIR) / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # Create file path with unique filename
        file_path = user_dir / unique_filename
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(content)
        
        file_path = str(file_path)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )

    # Create document record
    document = Document(
        user_id=user_id,
        title=title or file.filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        document_type=doc_type,
        mime_type=file.content_type or "application/octet-stream",
        processing_status=ProcessingStatus.PENDING,
    )

    if subject:
        document.subject = subject

    db.add(document)
    await db.commit()
    await db.refresh(document)

    # Process document based on type
    try:
        if doc_type == DocumentType.TXT:
            extracted_text = content.decode("utf-8-sig")
            if not extracted_text.strip():
                raise ValueError("The document contains no text.")
            document.extracted_text = extracted_text
            document.text_length = len(extracted_text)
            document.processing_status = ProcessingStatus.COMPLETED
            document.processed_at = datetime.utcnow()
        elif doc_type == DocumentType.PDF:
            extracted_text = await process_pdf(file_path)
            document.extracted_text = extracted_text
            document.text_length = len(extracted_text)
            document.processing_status = ProcessingStatus.COMPLETED
            document.processed_at = datetime.utcnow()
            
        elif doc_type == DocumentType.DOCX:
            extracted_text = await process_docx(file_path)
            document.extracted_text = extracted_text
            document.text_length = len(extracted_text)
            document.processing_status = ProcessingStatus.COMPLETED
            document.processed_at = datetime.utcnow()
            
        elif doc_type == DocumentType.AUDIO:
            extracted_text = await process_audio(file_path)
            document.extracted_text = extracted_text
            document.text_length = len(extracted_text)
            document.processing_status = ProcessingStatus.COMPLETED
            document.processed_at = datetime.utcnow()
            
        elif doc_type == DocumentType.IMAGE:
            extracted_text = await process_image(file_path)
            document.extracted_text = extracted_text
            document.text_length = len(extracted_text)
            document.processing_status = ProcessingStatus.COMPLETED
            document.processed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(document)
    except Exception as e:
        document.processing_status = ProcessingStatus.FAILED
        document.processing_error = str(e)
        await db.commit()

    return DocumentResponse.model_validate(document)


@router.get("/", response_model=List[DocumentListResponse])
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    subject: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    List all documents for the current user

    - **skip**: Number of documents to skip (pagination)
    - **limit**: Maximum number of documents to return
    - **subject**: Filter by subject
    """
    query = select(Document).where(Document.user_id == user_id)

    if subject:
        query = query.where(Document.subject == subject)

    query = query.order_by(desc(Document.created_at)).offset(skip).limit(limit)

    result = await db.execute(query)
    documents = result.scalars().all()

    return documents


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific document by ID
    """
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Increment view count
    document.view_count += 1
    await db.commit()
    await db.refresh(document)

    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a document
    """
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Delete physical file
    if os.path.exists(document.file_path):
        os.remove(document.file_path)

    # Delete from database
    await db.delete(document)
    await db.commit()

    return None


@router.get("/{document_id}/text")
async def get_document_text(
    document_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get extracted text from a document
    """
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if document.processing_status != ProcessingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document is still {document.processing_status.value}"
        )

    return {
        "document_id": document.id,
        "title": document.title,
        "text": document.extracted_text,
        "text_length": document.text_length,
        "page_count": document.page_count
    }


@router.post("/{document_id}/solve-problem")
async def solve_image_problem(
    document_id: int,
    problem_type: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Solve a problem from an uploaded image
    
    - **document_id**: ID of the image document
    - **problem_type**: Optional type (math, physics, chemistry, etc.)
    """
    # Get document
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if document.document_type != DocumentType.IMAGE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document is not an image"
        )

    if document.processing_status != ProcessingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document is still {document.processing_status.value}"
        )

    try:
        # Solve the problem from the image
        result = await solve_problem_from_image(document.file_path, problem_type)
        
        return {
            "document_id": document_id,
            "problem": result["extracted_text"],
            "solution": result["solution"],
            "problem_type": result["problem_type"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Problem solving failed: {str(e)}"
        )

@router.get("/{document_id}/search")
async def search_document(
    document_id: int,
    q: str = Query(..., min_length=1, max_length=200),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    document = await db.scalar(select(Document).where(Document.id == document_id, Document.user_id == user_id))
    if document is None:
        raise HTTPException(404, "Document not found")
    if document.processing_status != ProcessingStatus.COMPLETED:
        raise HTTPException(409, "Document text is not available yet.")
    query = q.strip().lower()
    if not query:
        raise HTTPException(400, "Enter a search query.")
    text = document.extracted_text or ""
    matches, offset = [], 0
    while len(matches) < 20:
        index = text.lower().find(query, offset)
        if index < 0:
            break
        matches.append({"title": document.title, "excerpt": text[max(0, index - 100):index + len(query) + 180], "relevance": "Text match"})
        offset = index + len(query)
    return {"results": matches}
