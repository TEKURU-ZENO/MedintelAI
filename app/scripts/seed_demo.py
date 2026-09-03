"""
app/scripts/seed_demo.py — Demo Data Generator

Seeds the database with a pre-configured "Struggling Learner" -> "Confident Learner"
progression, so the Showcase / Dashboard routes have rich data to display.
"""

import sys
import os
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import SessionLocal
from app.models.user import User
from app.models.submission import Submission
from app.models.result import Result
from app.models.practice_session import PracticeSession
from app.models.recommendation_feedback import RecommendationFeedback
from app.models.free_writing_session import FreeWritingSession
from app.core.security import get_password_hash

def seed_demo_data():
    db = SessionLocal()
    
    # 1. Create Demo User
    demo_email = "demo@aksharabyasa.com"
    user = db.query(User).filter(User.email == demo_email).first()
    
    if not user:
        user = User(
            email=demo_email,
            full_name="Demo Child",
            date_of_birth=date(2020, 1, 1),
            preferred_learning_mode="child",
            hashed_password=get_password_hash("demo"),
            xp_points=1450,
            level=3,
            user_streak=4
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Created demo user: {user.id}")

    # 2. Clear old data for idempotent seeding
    db.query(Result).filter(Result.submission_id.in_(
        db.query(Submission.id).filter(Submission.user_id == user.id)
    )).delete(synchronize_session=False)
    db.query(Submission).filter(Submission.user_id == user.id).delete()
    db.query(RecommendationFeedback).filter(RecommendationFeedback.user_id == user.id).delete()
    db.query(PracticeSession).filter(PracticeSession.user_id == user.id).delete()
    db.commit()

    # 3. Simulate "Struggling Learner" recovering
    base_time = datetime.utcnow() - timedelta(days=5)

    # Day 1: Struggles with A
    sess1 = PracticeSession(
        user_id=user.id,
        module_type="alphabet_practice",
        target_item="A",
        difficulty="beginner",
        is_completed=True,
        accuracy_score=0.45,
        duration_seconds=45,
        total_strokes=8,
        completed_at=base_time,
        status="completed"
    )
    db.add(sess1)
    db.commit()
    db.refresh(sess1)
    
    sub1 = Submission(user_id=user.id, input_type="canvas", created_at=base_time)
    db.add(sub1)
    db.commit()
    db.refresh(sub1)
    
    res1 = Result(
        submission_id=sub1.id,
        scores={"overall_score": 0.45, "overall": 0.45},
        features={"total_strokes": 8},
        feedback={"issues": [{"issue": "direction", "severity": "Medium", "message": "Direction failure", "score_impact": 5}]},
        confidence=0.9,
        created_at=base_time
    )
    db.add(res1)

    # Day 2: Replay-dependent on B
    sess2 = PracticeSession(
        user_id=user.id,
        module_type="alphabet_practice",
        target_item="B",
        difficulty="beginner",
        is_completed=True,
        accuracy_score=0.60,
        duration_seconds=30,
        total_strokes=4,
        completed_at=base_time + timedelta(days=1),
        status="completed"
    )
    db.add(sess2)
    db.commit()
    db.refresh(sess2)
    
    sub2 = Submission(user_id=user.id, input_type="canvas", created_at=base_time + timedelta(days=1))
    db.add(sub2)
    db.commit()
    db.refresh(sub2)
    
    res2 = Result(
        submission_id=sub2.id,
        scores={"overall_score": 0.60, "overall": 0.60},
        features={"total_strokes": 4},
        feedback={"issues": [{"issue": "hesitation", "severity": "Low", "message": "Hesitation detected", "score_impact": 2}]},
        confidence=0.95,
        created_at=base_time + timedelta(days=1)
    )
    db.add(res2)

    # Day 3: Confidence Boost - reviews A and succeeds
    sess3 = PracticeSession(
        user_id=user.id,
        module_type="alphabet_practice",
        target_item="A",
        difficulty="beginner",
        is_completed=True,
        accuracy_score=0.85,
        duration_seconds=15,
        total_strokes=3,
        completed_at=base_time + timedelta(days=2),
        status="completed"
    )
    db.add(sess3)
    db.commit()
    db.refresh(sess3)
    
    sub3 = Submission(user_id=user.id, input_type="canvas", created_at=base_time + timedelta(days=2))
    db.add(sub3)
    db.commit()
    db.refresh(sub3)
    
    res3 = Result(
        submission_id=sub3.id,
        scores={"overall_score": 0.85, "overall": 0.85},
        features={"total_strokes": 3},
        feedback={"issues": []},
        confidence=0.98,
        created_at=base_time + timedelta(days=2)
    )
    db.add(res3)

    # Day 4: Mastering CVC Words
    sess4 = PracticeSession(
        user_id=user.id,
        module_type="word_practice",
        target_item="CAT",
        difficulty="intermediate",
        is_completed=True,
        accuracy_score=0.92,
        duration_seconds=20,
        total_strokes=6,
        completed_at=base_time + timedelta(days=3),
        status="completed"
    )
    db.add(sess4)
    db.commit()
    db.refresh(sess4)
    
    sub4 = Submission(user_id=user.id, input_type="canvas", created_at=base_time + timedelta(days=3))
    db.add(sub4)
    db.commit()
    db.refresh(sub4)
    
    res4 = Result(
        submission_id=sub4.id,
        scores={"overall_score": 0.92, "overall": 0.92},
        features={"total_strokes": 6},
        feedback={"issues": []},
        confidence=0.99,
        created_at=base_time + timedelta(days=3)
    )
    db.add(res4)
    
    # 4. Add Feedback telemetry
    fb1 = RecommendationFeedback(user_id=user.id, item="A", action="completed", outcome_accuracy=0.85, module_type="alphabet_practice")
    fb2 = RecommendationFeedback(user_id=user.id, item="CAT", action="completed", outcome_accuracy=0.92, module_type="word_practice")
    db.add_all([fb1, fb2])

    db.commit()
    print("Seeded 'Struggling Learner -> Confident' journey successfully.")
    db.close()

if __name__ == "__main__":
    seed_demo_data()
