"""Practice and insights backed by the same user-scoped database as the library."""
from datetime import datetime, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.document import Document
from app.models.problem_attempt import ProblemAttempt, ProblemType

router = APIRouter()
# Curated exercises have deterministic scoring; answers remain on the server until submission.
BANK = {
    "math": [
        ("Solve for x: 2x + 5 = 13", ["4", "6", "8", "9"], 0, "Subtract 5 from both sides to get 2x = 8. Divide by 2: x = 4."),
        ("What is the derivative of x²?", ["x", "2x", "2", "x³ / 3"], 1, "The power rule gives d(xⁿ)/dx = nxⁿ⁻¹, so the derivative is 2x."),
        ("Find the mean of 2, 4, 6, and 8.", ["4", "6", "5", "20"], 2, "Add the values: 20. Divide by the four values: 20 / 4 = 5."),
    ],
    "physics": [
        ("A ball rises with initial speed 20 m/s. Using g = 9.8 m/s², what is its maximum height (ignoring air resistance)?", ["10.2 m", "40 m", "20.4 m", "9.8 m"], 2, "At the highest point v = 0. From v² = u² − 2gh, h = 400 / 19.6 ≈ 20.4 m."),
        ("A 2 kg object accelerates at 3 m/s². What is the net force?", ["1.5 N", "6 N", "5 N", "9 N"], 1, "Newton's second law: F = ma = 2 × 3 = 6 N."),
        ("What is the SI unit of energy?", ["Watt", "Newton", "Pascal", "Joule"], 3, "Energy is measured in joules. A joule is one newton-metre."),
    ],
    "chemistry": [
        ("Which equation is balanced?", ["H₂ + O₂ → H₂O", "2H₂ + O₂ → 2H₂O", "H₂ + 2O₂ → H₂O", "2H₂ + 2O₂ → H₂O"], 1, "2H₂ + O₂ → 2H₂O has four hydrogen atoms and two oxygen atoms on each side."),
        ("A solution with pH 3 is…", ["Acidic", "Neutral", "Basic", "Always pure water"], 0, "At standard conditions, a pH below 7 is acidic, 7 is neutral, and above 7 is basic."),
        ("The atomic number equals the number of…", ["Neutrons", "Protons and neutrons", "Protons", "Electron shells"], 2, "Atomic number counts the protons in a nucleus and identifies the element."),
    ],
    "biology": [
        ("Which organelle produces most ATP during aerobic respiration in eukaryotic cells?", ["Nucleus", "Ribosome", "Mitochondrion", "Golgi apparatus"], 2, "Mitochondria generate most ATP through aerobic cellular respiration."),
        ("Which molecule carries hereditary information?", ["DNA", "ATP", "Glucose", "Water"], 0, "DNA stores genetic instructions in its sequence of nucleotide bases."),
        ("Which gas do plants take in for photosynthesis?", ["Oxygen", "Carbon dioxide", "Nitrogen", "Hydrogen"], 1, "Plants use carbon dioxide and water, powered by light, to produce sugars and oxygen."),
    ],
}
NAMES = {"math": "Mathematics", "physics": "Physics", "chemistry": "Chemistry", "biology": "Biology"}

@router.get("/practice/{subject}")
async def practice_questions(subject: str):
    if subject not in BANK:
        raise HTTPException(404, "Subject not found")
    return {"questions": [{"id": f"{subject}-{i}", "question": row[0], "options": row[1]} for i, row in enumerate(BANK[subject])]}

class AttemptRequest(BaseModel):
    question_id: str = Field(..., max_length=30)
    option: int = Field(..., ge=0, le=3)

@router.post("/practice/attempts")
async def submit_attempt(request: AttemptRequest, user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    try:
        subject, index = request.question_id.rsplit("-", 1)
        if int(index) < 0:
            raise ValueError()
        question, options, answer, solution = BANK[subject][int(index)]
    except (ValueError, KeyError, IndexError):
        raise HTTPException(404, "Practice question not found")
    correct = request.option == answer
    db.add(ProblemAttempt(user_id=user_id, problem_type=ProblemType(subject), problem_text=question,
                          solution=solution, is_correct=correct, difficulty="introductory"))
    await db.commit()
    return {"correct": correct, "answer": options[answer], "solution": solution}

@router.get("/analytics")
async def learning_insights(period: Literal["week", "month", "semester"] = Query("week", alias="range"),
                            user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    today = datetime.utcnow().date()
    since = datetime.combine(today - timedelta(days={"week": 7, "month": 30, "semester": 180}[period] - 1), datetime.min.time())
    attempts = (await db.scalars(select(ProblemAttempt).where(ProblemAttempt.user_id == user_id, ProblemAttempt.created_at >= since).order_by(ProblemAttempt.created_at.desc()))).all()
    documents = (await db.scalars(select(Document).where(Document.user_id == user_id, Document.created_at >= since).order_by(Document.created_at.desc()))).all()
    correct = sum(item.is_correct is True for item in attempts)
    subjects = []
    for key, name in NAMES.items():
        rows = [item for item in attempts if item.problem_type.value == key]
        subjects.append({"subject": name, "attempts": len(rows), "score": round(100 * sum(item.is_correct is True for item in rows) / len(rows)) if rows else None})
    activity = [{"activity": f"Practiced {NAMES.get(item.problem_type.value, item.problem_type.value)}", "date": item.created_at.isoformat() + "Z", "result": "Correct" if item.is_correct else "Review needed"} for item in attempts]
    activity += [{"activity": f"Uploaded {item.title}", "date": item.created_at.isoformat() + "Z", "result": item.processing_status.value} for item in documents]
    activity.sort(key=lambda item: item["date"], reverse=True)
    daily = [{"date": (today - timedelta(days=6-i)).isoformat(), "count": sum(item.created_at.date() == today - timedelta(days=6-i) for item in attempts)} for i in range(7)]
    return {"attempts": len(attempts), "correct": correct, "accuracy": round(100 * correct / len(attempts)) if attempts else None,
            "documents": len(documents), "subjects": subjects, "daily": daily, "activity": activity[:20]}
