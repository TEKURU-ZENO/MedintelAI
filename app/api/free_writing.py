"""
app/api/free_writing.py — Free Writing Studio API

Endpoints:
  POST /studio/start           → create FreeWritingSession
  POST /studio/{id}/save       → auto-save strokes mid-session
  POST /studio/{id}/complete   → run quality engine, return WritingQualityReport
  GET  /studio/journey         → WritingProgressTrend for last 30 days
  GET  /studio/sessions        → paginated session history

Additions from product review:
  - session_intent (Addition 1)
  - emotional_state_snapshot (Addition 2) — stored automatically at complete
  - thumbnail_path (Addition 3) — client sends base64 PNG thumbnail
  - soft_goal (Addition 4) — optional pre-session goal
"""

import uuid
import os
import base64
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.logging import logger
from app.api.auth import get_current_user
from app.models.user import User
from app.models.free_writing_session import FreeWritingSession
from app.services.free_writing import (
    generate_quality_report,
    compute_progress_trend,
    normalize_strokes,
)

router = APIRouter()

THUMBNAIL_DIR = "thumbnails"
os.makedirs(THUMBNAIL_DIR, exist_ok=True)


# ── Schemas ───────────────────────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    session_intent: Literal["journaling", "practice", "doodling", "warmup", "story"] = "practice"
    soft_goal: Optional[str] = None
    canvas_width: int = 400
    canvas_height: int = 400


class SaveStrokesRequest(BaseModel):
    strokes: list[dict]


class CompleteSessionRequest(BaseModel):
    strokes: list[dict]
    duration_seconds: int
    thumbnail_base64: Optional[str] = None    # Addition 3: canvas PNG as base64


class StrokePoint(BaseModel):
    x: float
    y: float
    t: Optional[float] = None


# ── Helper: save thumbnail ────────────────────────────────────────────────────

def _save_thumbnail(session_id: str, b64_data: str) -> str | None:
    """Decodes base64 PNG and saves to THUMBNAIL_DIR. Returns relative path."""
    try:
        # Strip data URL prefix if present
        if "," in b64_data:
            b64_data = b64_data.split(",", 1)[1]
        img_bytes = base64.b64decode(b64_data)
        filename = f"{session_id}.png"
        path = os.path.join(THUMBNAIL_DIR, filename)
        with open(path, "wb") as f:
            f.write(img_bytes)
        return path
    except Exception as e:
        logger.warning(f"Failed to save thumbnail for session {session_id}: {e}")
        return None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/studio/start", tags=["Free Writing Studio"])
async def start_studio_session(
    body: StartSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new Free Writing Session and return its ID."""
    session = FreeWritingSession(
        id=uuid.uuid4(),
        user_id=current_user.id,
        session_intent=body.session_intent,
        soft_goal=body.soft_goal,
        canvas_width=body.canvas_width,
        canvas_height=body.canvas_height,
        status="active",
        started_at=datetime.utcnow(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    logger.info(f"[Studio] Session started: {session.id} for user {current_user.id} "
                f"intent={body.session_intent} goal={body.soft_goal}")

    return {
        "session_id": str(session.id),
        "status": "active",
        "intent": session.session_intent,
        "soft_goal": session.soft_goal,
    }


@router.post("/studio/{session_id}/save", tags=["Free Writing Studio"])
async def auto_save_session(
    session_id: str,
    body: SaveStrokesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Auto-save strokes mid-session (called every 15s from frontend)."""
    session = db.query(FreeWritingSession).filter(
        FreeWritingSession.id == session_id,
        FreeWritingSession.user_id == current_user.id,
        FreeWritingSession.status == "active",
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found or already completed")

    normalized_strokes = normalize_strokes(body.strokes)
    session.stroke_data = normalized_strokes
    session.stroke_count = len(normalized_strokes)
    db.commit()

    return {"status": "saved", "stroke_count": len(body.strokes)}


@router.post("/studio/{session_id}/complete", tags=["Free Writing Studio"])
async def complete_studio_session(
    session_id: str,
    body: CompleteSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Receives final strokes, runs the full quality engine pipeline,
    stores the report, and returns WritingQualityReport.
    """
    session = db.query(FreeWritingSession).filter(
        FreeWritingSession.id == session_id,
        FreeWritingSession.user_id == current_user.id,
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "completed":
        # Idempotent: return cached report
        return {"report": session.quality_metrics, "session_id": session_id}

    if not body.strokes:
        raise HTTPException(status_code=422, detail="No strokes provided")

    # Derive profile type for feedback tone
    profile_type = getattr(current_user, "profile_type", "child") or "child"

    # Get user streak for encouragement messages
    streak_days = getattr(current_user, "user_streak", 0) or 0

    # Check if improving (last 7 sessions trend)
    past_sessions = (
        db.query(FreeWritingSession)
        .filter(
            FreeWritingSession.user_id == current_user.id,
            FreeWritingSession.status == "completed",
        )
        .order_by(FreeWritingSession.completed_at)
        .limit(7)
        .all()
    )
    past_dicts = [{"overall_score": s.overall_score, "quality_metrics": s.quality_metrics,
                   "completed_at": s.completed_at} for s in past_sessions]
    from app.services.free_writing import compute_progress_trend
    trend = compute_progress_trend(past_dicts)

    # Normalize strokes to list format expected by engine and db consistency
    normalized_strokes = normalize_strokes(body.strokes)

    # Run quality engine
    report = generate_quality_report(
        session_id=session_id,
        strokes=normalized_strokes,
        canvas_width=float(session.canvas_width or 400),
        canvas_height=float(session.canvas_height or 400),
        profile_type=profile_type,
        is_improving=trend["is_improving"],
        streak_days=streak_days,
    )

    # Save thumbnail (Addition 3)
    thumbnail_path = None
    if body.thumbnail_base64:
        thumbnail_path = _save_thumbnail(session_id, body.thumbnail_base64)

    # Persist quality data and emotional snapshot
    session.stroke_data = normalized_strokes
    session.stroke_count = len(normalized_strokes)
    session.duration_seconds = body.duration_seconds
    session.quality_metrics = dict(report)
    session.overall_score = report["overall_quality_score"]
    session.quality_band = report["quality_band"]
    session.primary_strength = report["primary_strength"]
    session.primary_focus_area = report["primary_focus_area"]
    session.emotional_state_snapshot = dict(report["emotional_snapshot"])  # Addition 2
    session.thumbnail_path = thumbnail_path                                  # Addition 3
    session.status = "completed"
    session.completed_at = datetime.utcnow()

    db.commit()

    logger.info(f"[Studio] Session {session_id} completed: band={report['quality_band']} "
                f"score={report['overall_quality_score']}")

    return {
        "session_id": session_id,
        "report": report,
    }


@router.get("/studio/journey", tags=["Free Writing Studio"])
async def get_writing_journey(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns WritingProgressTrend for the user's last 30 sessions."""
    sessions = (
        db.query(FreeWritingSession)
        .filter(
            FreeWritingSession.user_id == current_user.id,
            FreeWritingSession.status == "completed",
        )
        .order_by(FreeWritingSession.completed_at)
        .limit(30)
        .all()
    )

    session_dicts = [
        {
            "overall_score": s.overall_score,
            "quality_metrics": s.quality_metrics,
            "completed_at": s.completed_at,
        }
        for s in sessions
    ]

    trend = compute_progress_trend(session_dicts)

    # Also return sparkline data (last 7 scores for chart)
    recent = sessions[-7:]
    sparkline = [
        {
            "date": s.completed_at.strftime("%a") if s.completed_at else "?",
            "score": round((s.overall_score or 0) * 100, 1),
            "band": s.quality_band,
        }
        for s in recent
    ]

    return {
        "trend": trend,
        "sparkline": sparkline,
        "total_sessions": len(sessions),
    }


@router.get("/studio/sessions", tags=["Free Writing Studio"])
async def list_studio_sessions(
    page: int = 1,
    per_page: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Paginated session history with quality metadata."""
    offset = (page - 1) * per_page
    sessions = (
        db.query(FreeWritingSession)
        .filter(FreeWritingSession.user_id == current_user.id)
        .order_by(FreeWritingSession.started_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return {
        "page": page,
        "sessions": [
            {
                "id": str(s.id),
                "intent": s.session_intent,
                "soft_goal": s.soft_goal,
                "quality_band": s.quality_band,
                "overall_score": s.overall_score,
                "duration_seconds": s.duration_seconds,
                "stroke_count": s.stroke_count,
                "thumbnail_path": s.thumbnail_path,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            }
            for s in sessions
        ],
    }
