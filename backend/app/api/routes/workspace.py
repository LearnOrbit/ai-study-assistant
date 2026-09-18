"""Practice and insights backed by the same user-scoped database as the library."""
from datetime import datetime, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.document import Document
from app.models.solved_problem import SolvedProblem
from app.models.flashcard import CardReview
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
    days = {"week": 7, "month": 30, "semester": 180}[period]
    since = datetime.combine(today - timedelta(days=days - 1), datetime.min.time())
    until = datetime.combine(today + timedelta(days=1), datetime.min.time())
    async def rows(model):
        return (await db.scalars(select(model).where(model.user_id == user_id,
            model.created_at >= since, model.created_at < until).order_by(model.created_at.desc()))).all()
    attempts = await rows(ProblemAttempt)
    documents = await rows(Document)
    solutions = await rows(SolvedProblem)
    reviews = await rows(CardReview)
    graded = [item for item in attempts if item.is_correct is not None]
    correct = sum(item.is_correct is True for item in graded)
    subjects = []
    for key, name in NAMES.items():
        items = [item for item in graded if item.problem_type.value == key]
        subjects.append({"subject": name, "attempts": len(items),
            "score": round(100 * sum(item.is_correct is True for item in items) / len(items)) if items else None})
    activity = [{"activity": f"Practiced {NAMES.get(item.problem_type.value, item.problem_type.value)}",
                 "date": item.created_at.isoformat() + "Z", "result": "Not graded" if item.is_correct is None else "Correct" if item.is_correct else "Review needed"} for item in attempts]
    activity += [{"activity": f"Uploaded {item.title}", "date": item.created_at.isoformat() + "Z", "result": item.processing_status.value} for item in documents]
    activity += [{"activity": f"Explored a {item.subject} solution", "date": item.created_at.isoformat() + "Z", "result": "AI explanation"} for item in solutions]
    activity += [{"activity": "Reviewed a flashcard", "date": item.created_at.isoformat() + "Z", "result": item.rating} for item in reviews]
    activity.sort(key=lambda item: item["date"], reverse=True)
    counts = {}
    for kind, items in [("practice", attempts), ("solutions", solutions), ("reviews", reviews), ("uploads", documents)]:
        for item in items:
            day = item.created_at.date().isoformat()
            counts.setdefault(day, {"practice": 0, "solutions": 0, "reviews": 0, "uploads": 0})[kind] += 1
    daily = []
    for i in range(days):
        day = (since.date() + timedelta(days=i)).isoformat()
        tally = counts.get(day, {"practice": 0, "solutions": 0, "reviews": 0, "uploads": 0})
        daily.append({"date": day, "count": tally["practice"], "total": sum(tally.values()), **tally})
    # Streak is independent of the reporting period. Today or yesterday can anchor it.
    dates = union_all(*[select(func.date(model.created_at).label("day")).where(
        model.user_id == user_id, model.created_at < until) for model in [ProblemAttempt, SolvedProblem, CardReview, Document]]).subquery()
    active_dates = set((await db.scalars(select(dates.c.day).distinct())).all())
    cursor = today if today.isoformat() in active_dates else today - timedelta(days=1)
    streak = 0
    while cursor.isoformat() in active_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return {"attempts": len(attempts), "graded_attempts": len(graded), "correct": correct,
            "accuracy": round(100 * correct / len(graded)) if graded else None,
            "documents": len(documents), "solutions": len(solutions), "reviews": len(reviews),
            "review_ratings": {rating: sum(r.rating == rating for r in reviews) for rating in ["again", "hard", "good", "easy"]},
            "active_days": sum(day["total"] > 0 for day in daily), "streak": streak,
            "subjects": subjects, "daily": daily, "activity": activity[:20], "timezone": "UTC"}
