from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from pathlib import Path

from app.core.database import engine, Base
from app.api.routes import auth, documents, summarization, questions, workspace
from app.api import chat_routes  # ✅ ONLY CHANGE: Import chat_routes instead of chat
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup: Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # The existing local demo uses user 1; ensure uploads have a real owner.
    from app.core.security import TESTING_MODE, TEST_USER_ID
    from app.core.database import AsyncSessionLocal
    from app.models.user import User
    if TESTING_MODE:
        async with AsyncSessionLocal() as db:
            if await db.get(User, TEST_USER_ID) is None:
                db.add(User(id=TEST_USER_ID, email="local-study@example.invalid",
                            username="local-study", hashed_password="!disabled"))
                await db.commit()

    # Create necessary directories
    os.makedirs("uploads/images", exist_ok=True)
    os.makedirs("uploads/documents", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    print("\n🚀 AI Study Assistant is starting up...")
    print(f"📋 Query Validator: {'✅ Enabled' if settings.enable_ai_validation else '❌ Disabled'}")
    print(f"📸 Image Upload: {'✅ Enabled' if hasattr(settings, 'gemini_api_key') else '⚠️  Configure API key'}")
    print(f"💾 Database: ✅ Connected")
    print(f"📁 Upload Directory: ✅ Ready")

    yield

    # Shutdown: Close database connections
    print("\n👋 Shutting down AI Study Assistant...")
    await engine.dispose()


app = FastAPI(
    title="AI Study Assistant",
    description="AI-powered study assistant with image question solving, document processing, and chat",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for serving uploaded images
app.mount("/uploads", StaticFiles(directory=settings.upload_dir, check_dir=False), name="uploads")

# Include routers
app.include_router(workspace.router, prefix="/api", tags=["Workspace"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(questions.router, prefix="/api/questions", tags=["Questions"])
app.include_router(chat_routes.router, tags=["Chat"])  # ✅ ONLY CHANGE: Use chat_routes.router
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(summarization.router, prefix="/api/summarize", tags=["Summarization"])


@app.get("/")
def read_root():
    return {
        "message": "AI Study Assistant API",
        "version": "1.0.0",
        "status": "running",
        "features": {
            "authentication": "enabled",
            "image_questions": "enabled",
            "chat": "enabled",
            "documents": "enabled",
            "summarization": "enabled",
            "query_validation": "enabled" if settings.enable_ai_validation else "disabled"
        },
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "upload_question": "/api/questions/upload"
        }
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "AI Study Assistant",
        "database": "connected",
        "query_validator": {
            "enabled": settings.enable_ai_validation,
            "mode": "strict" if settings.strict_validation_mode else "flexible",
            "api_configured": bool(settings.gemini_api_key)
        },
        "image_processing": {
            "enabled": bool(settings.gemini_api_key),
            "upload_directory": "uploads/images",
            "max_file_size": "10MB"
        }
    }


@app.get("/api/stats")
async def get_stats():
    """Get system statistics"""
    upload_dir = Path("uploads/images")
    total_images = len(list(upload_dir.glob("*"))) if upload_dir.exists() else 0
    
    return {
        "total_uploads": total_images,
        "storage_available": True,
        "api_status": "operational"
    }