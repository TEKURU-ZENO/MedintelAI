from datetime import date
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Literal


# ──────────────────────────────────────────────────────────────────────────────
# Auth Schemas — V2 Unified Profile System
# ──────────────────────────────────────────────────────────────────────────────

ProfileType = Literal["early_learner", "child", "adult"]


class UserCreate(BaseModel):
    """Schema for new user registration."""
    email: EmailStr
    password: str
    full_name: str
    date_of_birth: date             # ISO format: "2005-03-15"
    parent_id: int | None = None    # Optional — can be linked later
    preferred_learning_mode: ProfileType | None = None  # Optional teacher/admin override


class UserResponse(BaseModel):
    """
    Public user representation returned by /auth/profile and /auth/register.
    profile_type is serialized from the @property on the ORM model.
    """
    id: int
    email: EmailStr
    full_name: str | None
    is_active: bool
    profile_type: str           # derived: "early_learner" | "child" | "adult"
    preferred_learning_mode: str | None
    preferred_language: str
    level: int
    xp_points: int
    user_streak: int
    pending_parent_link: bool

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdateRequest(BaseModel):
    """Schema for updating user profile preferences."""
    full_name: str | None = None
    preferred_learning_mode: ProfileType | None = None
    preferred_language: str | None = None


class UIConfig(BaseModel):
    """Schema for the adaptive UI configuration returned to the frontend."""
    profile_type: ProfileType
    theme: str
    font_size: str
    animations: bool
    sounds: bool
    confetti: bool
    tts_speed: str
    difficulty_default: str
    feedback_tone: str
    gamification: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Data embedded in JWT payload."""
    email: str | None = None
    user_id: int | None = None
    # JWT is NOT source of truth for profile_type.
    # Frontend fetches /auth/profile after login for full hydration.
