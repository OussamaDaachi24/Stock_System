"""Bootstrap script: creates default admin user if none exist."""
from app.db import Base, SessionLocal, engine
from app.models import User
from app.security import hash_password


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).filter(User.role == "admin").first():
            print("Admin already exists; skipping.")
            return
        admin = User(
            email="admin@example.com",
            name="Default Admin",
            password_hash=hash_password("ChangeMe123!"),
            role="admin",
            status="active",
        )
        db.add(admin)
        db.commit()
        print("Created admin: admin@example.com / ChangeMe123!")
    finally:
        db.close()


if __name__ == "__main__":
    main()
