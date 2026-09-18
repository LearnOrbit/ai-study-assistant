from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    learning_profile = relationship("LearningProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    problem_attempts = relationship("ProblemAttempt", back_populates="user", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="user", cascade="all, delete-orphan")
    # Question History relationship
    question_history = relationship("QuestionHistory", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
