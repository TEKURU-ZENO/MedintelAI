from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.ai_service import AIService
from app.services.gamification import GamificationService
from app.services.progress_service import ProgressService
from app.services.tts_service import TTSService
from app.services.tracing_service import TracingService
from app.services.streak_service import StreakService
from app.services.ml_service import MLService
from app.services.difficulty_service import DifficultyService
from app.data.letters import LETTER_POINTS
from app.models.submission import Submission, InputType
from app.repositories.result_repo import save_result
from app.api.auth import get_current_user
import json
import os

router = APIRouter(prefix="/analysis")

ai_service = AIService()
gamification_service = GamificationService()
progress_service = ProgressService()
tts_service = TTSService()
tracing_service = TracingService()
streak_service = StreakService()
ml_service = MLService()
difficulty_service = DifficultyService()

def update_metrics(score):
    monitoring_file = "monitoring.json"
    try:
        with open(monitoring_file, "r") as f:
            data = json.load(f)
    except:
        data = {"runs": 0, "avg_score": 0}

    data["runs"] += 1
    data["avg_score"] = (
        (data["avg_score"] * (data["runs"] - 1) + score)
        / data["runs"]
    )

    with open(monitoring_file, "w") as f:
        json.dump(data, f)

@router.post("/run")
async def run_analysis(
    input_type: InputType = Form(...),
    file: UploadFile = File(None),
    canvas_data: str = Form(None),  # base64
    strokes: str = Form(None),      # JSON string
    letter: str = Form(None),       # Target letter for tracing
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):

    # --- 1. VALIDATION ---
    if input_type == InputType.IMAGE and not file:
        raise HTTPException(400, "Image file required")

    if input_type == InputType.CANVAS and not canvas_data:
        raise HTTPException(400, "Canvas data required")

    # --- 2. CREATE SUBMISSION ---
    submission = Submission(
        user_id=user.id,
        input_type=input_type,
        image_path=None,
        stroke_data=json.loads(strokes) if strokes else None,
    )

    db.add(submission)
    db.commit()
    db.refresh(submission)

    # --- 3. RUN AI ---
    ai_output = await ai_service.process(
        input_type=input_type,
        file=file,
        strokes=json.loads(strokes) if strokes else None,
        base64_image=canvas_data,
    )

    # --- 3.5 TRACING (GUIDED PRACTICE) ---
    if input_type == InputType.CANVAS and letter and strokes:
        strokes_data = json.loads(strokes)
        expected = LETTER_POINTS.get(letter, [])
        tracing_result = tracing_service.evaluate(strokes_data, expected)
        ai_output["tracing"] = tracing_result

    # --- 3.6 GAMIFICATION & PROGRESS ---
    gamified = gamification_service.apply(
        scores=ai_output.get("scores", {}),
        level=2  # Defaulting to 2 for now, can be dynamic based on User model later
    )

    progress = progress_service.compute_progress(
        db,
        user.id,
        gamified["adjusted_score"]
    )

    # --- 3.6 AUDIO (TTS) ---
    feedback_list = ai_output.get("feedback", [])
    # AI output feedback can be a list of strings or dicts. Extract strings safely.
    feedback_strings = []
    for item in feedback_list:
        if isinstance(item, dict):
            feedback_strings.append(item.get("message", ""))
        else:
            feedback_strings.append(str(item))
            
    combined_feedback = " ".join(feedback_strings)
    audio_path = tts_service.generate(combined_feedback)

    # --- 3.7 ML SHADOW SCORING ---
    ml_score = ml_service.predict(ai_output.get("features", {}))
    ai_output["ml_score"] = ml_score
    ai_output["score_delta"] = ml_score - gamified["adjusted_score"]

    # --- 4. SAVE RESULT & STREAK ---
    # Update ai_output scores with adjusted score for history tracking if needed
    if "scores" not in ai_output:
        ai_output["scores"] = {}
    ai_output["scores"]["overall_score"] = gamified["adjusted_score"]
    
    # Inject audio path back into output payload for repository
    ai_output["audio_path"] = audio_path
    
    result = save_result(db, submission.id, ai_output)
    
    # Update streak
    current_streak = streak_service.update_streak(user)
    db.commit()
    
    # --- 4.5 MONITORING ---
    update_metrics(gamified["adjusted_score"])

    # --- 5. RESPONSE ---
    return {
        "submission_id": submission.id,
        "scores": result.scores,
        "gamification": gamified,
        "progress": progress,
        "streak": current_streak,
        "difficulty": difficulty_service.get_level(user),
        "tracing": ai_output.get("tracing"),
        "feedback": result.feedback,
        "confidence": result.confidence,
        "audio_url": result.audio_path,
        "features": result.features,
    }
