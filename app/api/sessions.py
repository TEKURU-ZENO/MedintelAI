"""
app/api/sessions.py — Session & Module Endpoints

All routes delegate to the LearningEngine.
Route handlers are intentionally thin — no business logic here.

Endpoints:
  POST   /sessions/start
  POST   /sessions/{id}/complete
  POST   /sessions/{id}/abandon
  PATCH  /sessions/{id}/strokes      (auto-save in-progress strokes)
  GET    /sessions/history
  GET    /sessions/modules            (profile-aware module list)
  GET    /sessions/modules/{type}/item  (get next recommended item)
  GET    /sessions/modules/{type}/data/{item}  (get item tracing data)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.practice_session import PracticeSession
from app.schemas.session import (
    SessionStart,
    SessionComplete,
    SessionAbandon,
    SessionResponse,
    SessionCompleteResponse,
    ModuleItemResponse,
    ModuleListResponse,
    GuidanceEvent,
    GuidanceResponse,
    RecommendedDifficultyResponse,
)
from app.services.learning_engine import (
    start_session,
    complete_session,
    abandon_session,
    update_session_strokes,
    get_module_item,
    get_modules_for_user,
    get_next_item,
)
from app.services.guidance_handler import process_guidance_event
from app.services.difficulty_adapter import get_recommended_difficulty

router = APIRouter()


# ── Helper ────────────────────────────────────────────────────────────────────

def get_session_or_404(
    session_id: int,
    user: User,
    db: Session,
) -> PracticeSession:
    """Fetch a session that belongs to the current user."""
    sess = (
        db.query(PracticeSession)
        .filter(
            PracticeSession.id      == session_id,
            PracticeSession.user_id == user.id,
        )
        .first()
    )
    if sess is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found.",
        )
    return sess


# ── Session lifecycle ─────────────────────────────────────────────────────────

@router.post("/start", response_model=SessionResponse, status_code=201)
def start_practice_session(
    body: SessionStart,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Begin a new practice session.
    Returns the session record — frontend stores session_id for /complete call.
    """
    sess = start_session(
        user        = current_user,
        module_type = body.module_type,
        target_item = body.target_item,
        language    = body.language,
        difficulty  = body.difficulty,
        db          = db,
    )
    return sess


@router.post("/{session_id}/complete", response_model=SessionCompleteResponse)
def complete_practice_session(
    session_id: int,
    body: SessionComplete,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark a session complete, award XP, update streak.
    Returns reward payload for the frontend celebration UI.
    """
    sess = get_session_or_404(session_id, current_user, db)

    if sess.is_completed:
        raise HTTPException(
            status_code=400,
            detail="This session is already completed.",
        )

    result = complete_session(
        session          = sess,
        user             = current_user,
        accuracy_score   = body.accuracy_score,
        detailed_scores  = body.detailed_scores,
        duration_seconds = body.duration_seconds,
        stroke_data      = body.stroke_data,
        total_strokes    = body.total_strokes,
        total_points     = body.total_points,
        db               = db,
    )
    return result


@router.post("/{session_id}/abandon", response_model=SessionResponse)
def abandon_practice_session(
    session_id: int,
    body: SessionAbandon,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark a session abandoned (partial strokes saved, no XP awarded).
    """
    sess = get_session_or_404(session_id, current_user, db)
    result = abandon_session(
        session    = sess,
        stroke_data = body.stroke_data,
        reason     = body.reason,
        db         = db,
    )
    return result


@router.patch("/{session_id}/strokes", response_model=SessionResponse)
def save_strokes(
    session_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Auto-save in-progress stroke data (called every N seconds by the canvas).
    Does not complete the session — just persists the current stroke state.
    """
    sess = get_session_or_404(session_id, current_user, db)
    result = update_session_strokes(
        session    = sess,
        stroke_data = body.get("stroke_data"),
        db         = db,
    )
    return result


# ── History ───────────────────────────────────────────────────────────────────

@router.get("/history", response_model=list[SessionResponse])
def get_session_history(
    limit: int = Query(default=20, ge=1, le=100),
    module_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return session history for the current user.
    Optional filter by module_type.
    """
    query = (
        db.query(PracticeSession)
        .filter(PracticeSession.user_id == current_user.id)
        .order_by(PracticeSession.started_at.desc())
    )
    if module_type:
        query = query.filter(PracticeSession.module_type == module_type)
    return query.limit(limit).all()


# ── Module discovery ──────────────────────────────────────────────────────────

@router.get("/modules", response_model=ModuleListResponse)
def list_modules(
    current_user: User = Depends(get_current_user),
):
    """
    Return modules available for the current user's profile type.
    Used by shell module-selection screens.
    """
    modules = get_modules_for_user(current_user)
    return {
        "profile_type": current_user.profile_type,
        "modules": modules,
    }


@router.get("/modules/{module_type}/item", response_model=ModuleItemResponse)
def get_next_module_item(
    module_type: str,
    difficulty: str = Query(default="beginner"),
    language: str   = Query(default="english"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the recommended next item for a practice session.
    Uses least-practiced round-robin strategy (Phase 11: ML replacement).
    """
    item = get_next_item(module_type, difficulty, current_user.id, db, language)
    if not item:
        raise HTTPException(
            status_code=404,
            detail=f"No items available for module '{module_type}'.",
        )
    try:
        data = get_module_item(module_type, item, language)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return data


@router.get("/modules/{module_type}/data/{item}", response_model=ModuleItemResponse)
def get_module_item_data(
    module_type: str,
    item: str,
    language: str   = Query(default="english"),
    current_user: User = Depends(get_current_user),
):
    """
    Get specific tracing/practice data for an item.
    """
    try:
        data = get_module_item(module_type, item, language)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return data


@router.get("/modules/{module_type}/recommended-difficulty",
            response_model=RecommendedDifficultyResponse)
def recommended_difficulty(
    module_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return the recommended next difficulty for a module based on
    recent session performance (promotes at ≥0.85, demotes at ≤0.50).
    """
    return get_recommended_difficulty(current_user.id, module_type, db)


@router.post("/{session_id}/guidance-event", response_model=dict)
def handle_guidance_event(
    session_id: int,
    body: GuidanceEvent,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Process a single stroke guidance event mid-session.
    Frontend sends this after each stroke ends for authoritative scoring.
    Returns: scores, direction detection, feedback, unlock signal.
    """
    sess = get_session_or_404(session_id, current_user, db)

    if sess.is_completed:
        raise HTTPException(status_code=400, detail="Session already completed.")

    # Load or initialise per-stroke attempt counts from session's detailed_scores
    attempt_counts = {}
    if sess.detailed_scores and "stroke_attempt_counts" in sess.detailed_scores:
        attempt_counts = sess.detailed_scores["stroke_attempt_counts"]

    # Get user profile type for feedback tone
    profile_type = current_user.profile_type

    # Allow frontend to override target_item and module_type (e.g. tracing active letter in spelling session)
    module_type = body.module_type or sess.module_type
    target_item = body.target_item or sess.target_item or ""

    result = process_guidance_event(
        session_id          = session_id,
        module_type         = module_type,
        target_item         = target_item,
        event               = body.model_dump(),
        stroke_attempt_counts = attempt_counts,
        profile_type        = profile_type,
    )

    # Persist updated attempt counts + inactivity data
    merged_scores = sess.detailed_scores or {}
    merged_scores["stroke_attempt_counts"] = attempt_counts
    if body.hesitation_ms is not None:
        hesitations = merged_scores.get("hesitation_ms_per_stroke", [])
        hesitations.append({"stroke_id": body.stroke_id, "ms": body.hesitation_ms})
        merged_scores["hesitation_ms_per_stroke"] = hesitations
    sess.detailed_scores = merged_scores
    db.commit()

    return result
