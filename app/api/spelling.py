"""
app/api/spelling.py — Spelling & Literacy API

Serves the literacy orchestrator payload.
"""

from fastapi import APIRouter
from app.services.spelling.literacy_orchestrator import generate_literacy_session_config
from app.services.spelling.spelling_state_machine import SpellingProgression
from pydantic import BaseModel

router = APIRouter()

@router.get("/config")
def get_spelling_config(word: str, learning_style: str = "adult", profile_type: str = "child"):
    """Returns the full spelling orchestrator payload for the frontend."""
    return generate_literacy_session_config(word, learning_style, profile_type)

class SpellingAttemptRequest(BaseModel):
    target_word: str
    current_progress: list[str]
    attempted_letter: str

@router.post("/attempt")
def validate_spelling_attempt(req: SpellingAttemptRequest):
    """
    Stateless spelling progression validation.
    Returns the new spelling state and next expected letter.
    """
    prog = SpellingProgression(req.target_word)
    prog.progress = req.current_progress
    
    return prog.process_attempt(req.attempted_letter)
