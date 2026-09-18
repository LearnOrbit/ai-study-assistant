from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class Deck(Base):
    __tablename__ = "flashcard_decks"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(120), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class Flashcard(Base):
    __tablename__ = "flashcards"
    id = Column(Integer, primary_key=True)
    deck_id = Column(Integer, ForeignKey("flashcard_decks.id"), nullable=False, index=True)
    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)
    interval_days = Column(Integer, nullable=False, default=0)
    version = Column(Integer, nullable=False, default=0)
    due_at = Column(DateTime, server_default=func.now(), nullable=False)

class CardReview(Base):
    __tablename__ = "flashcard_reviews"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    card_id = Column(Integer, ForeignKey("flashcards.id"), nullable=False, index=True)
    rating = Column(String(10), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
