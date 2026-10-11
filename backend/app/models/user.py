from datetime import date as date_type
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


# ──────────────────────────────────────────────────────────────────────────────
# User Model — V2 Unified Profile System
# Profile type is DERIVED at runtime from date_of_birth + preferred_learning_mode.
# We do NOT store profile_type as a column — it is a @property so it self-updates
# as users age without any migration needed.
# ──────────────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # ── Identity ──────────────────────────────────────────────────────────────
    full_name = Column(String, nullable=True)
    date_of_birth = Column(Date, nullable=True)

    # ── Hierarchy ─────────────────────────────────────────────────────────────
    # Self-referential FK: child users point to their parent's user.id
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # True for users ≤ 15 who registered without linking a parent yet
    pending_parent_link = Column(Boolean, default=False)

    # ── Adaptive Overrides ────────────────────────────────────────────────────
    # Optional manual override: if set, takes precedence over age-derived type.
    # Values: "early_learner" | "child" | "adult" | None
    preferred_learning_mode = Column(String, nullable=True)

    # ── Language ─────────────────────────────────────────────────────────────
    # Phase 10 multi-language expansion — nullable now, used later
    preferred_language = Column(String, default="english", nullable=False)

    # ── Progression ──────────────────────────────────────────────────────────
    level = Column(Integer, default=1, nullable=False)
    xp_points = Column(Integer, default=0, nullable=False)

    # ── Retention Engine ─────────────────────────────────────────────────────
    user_streak    = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)   # Phase 3.5: tracks all-time best
    last_active_date = Column(Date, nullable=True)

    # ── Legacy (safe rename — will be dropped in Phase 2) ────────────────────
    # The old "role" column is preserved here under a new name so existing
    # sessions / data are not destroyed. Alembic will rename it, not drop it.
    _legacy_role = Column("_legacy_role", String, nullable=True)

    # ── Status ───────────────────────────────────────────────────────────────
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ──────────────────────────────────────────────────────────
    from sqlalchemy.orm import relationship
    free_writing_sessions = relationship("FreeWritingSession", back_populates="user", cascade="all, delete-orphan")

    # ─────────────────────────────────────────────────────────────────────────
    # Derived Properties — NOT stored in DB
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def age(self) -> int | None:
        """Calculate current age in years from date_of_birth."""
        if self.date_of_birth is None:
            return None
        today = date_type.today()
        dob = self.date_of_birth
        return (
            today.year
            - dob.year
            - ((today.month, today.day) < (dob.month, dob.day))
        )

    @property
    def age_derived_profile(self) -> str:
        """Derive profile type from age alone (no overrides)."""
        age = self.age
        if age is None:
            return "adult"      # safe default for users with no DOB
        if age <= 5:
            return "early_learner"
        if age <= 15:
            return "child"
        return "adult"

    @property
    def profile_type(self) -> str:
        """
        Effective profile type used for all adaptive rendering.
        preferred_learning_mode (set by user/teacher/admin) takes precedence
        over the age-derived value. This allows:
          - Adult beginners to use early_learner mode
          - Special education overrides
          - Teacher-assigned profiles
        """
        if self.preferred_learning_mode in ("early_learner", "child", "adult"):
            return self.preferred_learning_mode
        return self.age_derived_profile
