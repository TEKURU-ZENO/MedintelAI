from sqlalchemy.orm import Session
from app.models.result import Result
from app.models.submission import Submission

class ProgressService:

    def get_recent_results(self, db: Session, user_id: int, limit=3):
        return (
            db.query(Result)
            .join(Submission, Result.submission_id == Submission.id)
            .filter(Submission.user_id == user_id)
            .order_by(Result.created_at.desc())
            .limit(limit)
            .all()
        )

    def compute_progress(self, db: Session, user_id: int, new_score: float):
        history = self.get_recent_results(db, user_id)

        # Assuming the score we track for progress is the "overall_score" from the JSONB
        # Or we can just extract whatever was saved. Let's use overall_score.
        past_scores = []
        for r in history:
            if r.scores and "overall_score" in r.scores:
                past_scores.append(r.scores.get("overall_score"))
            elif r.scores and "overall" in r.scores:
                past_scores.append(r.scores.get("overall"))

        # Smoothed score
        all_scores = past_scores + [new_score]
        smoothed = sum(all_scores) / len(all_scores)

        # Improvement detection
        improvement = False
        if past_scores:
            # past_scores[0] is the most recent past score due to order_by desc
            improvement = new_score > past_scores[0] + 3

        return {
            "smoothed_score": smoothed,
            "improved": improvement,
        }
