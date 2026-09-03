"""
auth.py — V2 Authentication & Profile Endpoints

Architecture note:
  - JWT contains ONLY: sub (email) + user_id
  - JWT is NOT the source of truth for profile_type
  - Frontend flow after login:
      1. POST /auth/login → receive JWT, store in localStorage
      2. GET  /auth/profile → hydrate full app state (profile_type, level, etc.)
      3. GET  /auth/me/ui-config → get adaptive UI configuration
  This ensures profile changes (DOB update, mode override) are always fresh.
"""

from datetime import timedelta, date as date_type
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import (
    UserCreate,
    UserResponse,
    Token,
    TokenData,
    ProfileUpdateRequest,
    UIConfig,
)
from app.services.profile_service import get_learning_profile

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# ──────────────────────────────────────────────────────────────────────────────
# Dependency: get current authenticated user
# ──────────────────────────────────────────────────────────────────────────────

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    from jose import JWTError, jwt

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user


# ──────────────────────────────────────────────────────────────────────────────
# Registration
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user with full profile data.
    Automatically sets pending_parent_link=True for users aged ≤ 15
    who don't supply a parent_id at registration time.
    """
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists.",
        )

    # Calculate age to determine pending_parent_link flag
    today = date_type.today()
    dob = user_in.date_of_birth
    age = (
        today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    )
    is_minor = age <= 15
    needs_parent_link = is_minor and user_in.parent_id is None

    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        date_of_birth=user_in.date_of_birth,
        parent_id=user_in.parent_id,
        pending_parent_link=needs_parent_link,
        preferred_learning_mode=user_in.preferred_learning_mode,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ──────────────────────────────────────────────────────────────────────────────
# Login
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    Authenticate and return a JWT.
    JWT payload contains only: sub (email) + user_id.
    Frontend MUST call /auth/profile after login to hydrate profile state.
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ──────────────────────────────────────────────────────────────────────────────
# Profile (source of truth for frontend app state)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/profile", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    """
    Return the full user profile including derived profile_type.
    Frontend calls this immediately after login and on profile changes.
    This is the source of truth — not the JWT payload.
    """
    return current_user


@router.patch("/profile", response_model=UserResponse)
def update_profile(
    updates: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update mutable profile fields.
    Allows users (or teachers/admins) to override learning mode.
    """
    if updates.full_name is not None:
        current_user.full_name = updates.full_name
    if updates.preferred_learning_mode is not None:
        current_user.preferred_learning_mode = updates.preferred_learning_mode
    if updates.preferred_language is not None:
        current_user.preferred_language = updates.preferred_language

    db.commit()
    db.refresh(current_user)
    return current_user


# ──────────────────────────────────────────────────────────────────────────────
# UI Config (adaptive frontend config — cache on frontend, refresh on changes)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/me/ui-config", response_model=UIConfig)
def get_ui_config(current_user: User = Depends(get_current_user)):
    """
    Return adaptive UI configuration for the authenticated user.
    Frontend should cache this in context + localStorage.
    Only needs to be re-fetched on login or profile update.
    """
    profile = get_learning_profile(current_user)
    return UIConfig(**profile)
