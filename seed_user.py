from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash

def seed():
    db = SessionLocal()
    email = "parent@test.com"
    password = "password123"
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            role=UserRole.PARENT
        )
        db.add(user)
        db.commit()
        print(f"Test user created! Email: {email} | Password: {password}")
    else:
        print(f"Test user already exists! Email: {email} | Password: {password}")
    
    db.close()

if __name__ == "__main__":
    seed()
