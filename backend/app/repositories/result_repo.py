from sqlalchemy.orm import Session
from app.models.result import Result

def save_result(db: Session, submission_id: int, ai_output: dict) -> Result:
    result = Result(
        submission_id=submission_id,
        features=ai_output.get("features", {}),
        scores=ai_output.get("scores", {}),
        feedback=ai_output.get("feedback", {}),
        confidence=ai_output.get("confidence", 0.0),
        audio_path=ai_output.get("audio_path"),
    )

    db.add(result)
    db.commit()
    db.refresh(result)

    return result
