from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.result import Result
from app.models.submission import Submission

router = APIRouter(prefix="/analytics")

@router.get("/history")
def get_history(db: Session = Depends(get_db), user=Depends(get_current_user)):
    results = (
        db.query(Result)
        .join(Submission)
        .filter(Submission.user_id == user.id)
        .order_by(Result.created_at.asc())
        .all()
    )

    return [
        {
            "score": r.scores.get("overall_score", r.scores.get("overall", 0)) if r.scores else 0,
            "date": r.created_at.isoformat() if r.created_at else None
        }
        for r in results
    ]
