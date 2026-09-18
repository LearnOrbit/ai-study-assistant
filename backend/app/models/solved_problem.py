from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class SolvedProblem(Base):
    __tablename__ = "solved_problems"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    problem = Column(Text, nullable=False)
    subject = Column(String(30), nullable=False)
    result = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
