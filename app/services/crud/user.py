# services/crud/user.py
from sqlmodel import Session, select
from models import User
from typing import Optional
from auth.hash_password import HashPassword

hash_password = HashPassword()


def get_user_by_email(email: str, session: Session) -> Optional[User]:
    return session.exec(select(User).where(User.email == email)).first()


def get_user_by_id(session: Session, user_id: int) -> Optional[User]:
    return session.get(User, user_id)


def create_user(session: Session, email: str, password: str, name: Optional[str] = None, role: str = "user") -> User:
    hashed = hash_password.create_hash(password)
    user = User(email=email, hashed_password=hashed, name=name, role=role)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def update_user(session: Session, user_id: int, **kwargs) -> Optional[User]:
    user = get_user_by_id(session, user_id)
    if not user:
        return None
    for key, value in kwargs.items():
        if hasattr(user, key) and value is not None:
            setattr(user, key, value)
    session.commit()
    session.refresh(user)
    return user


def delete_user(session: Session, user_id: int) -> bool:
    user = get_user_by_id(session, user_id)
    if not user:
        return False
    session.delete(user)
    session.commit()
    return True


def create_default_users(session: Session):
    print("Создаем пользователей по умолчанию...")
    defaults = [
        ("admin@example.com", "adminpass", "Admin User", "admin", True),
        ("observer@example.com", "observerpass", "Observer", "observer", False),
        ("user@example.com", "userpass", "Regular User", "user", False)
    ]

    created_count = 0
    for email, password, name, role, is_super in defaults:
        if not get_user_by_email(email, session):
            user = create_user(session, email, password, name=name, role=role)
            user.is_superuser = is_super
            session.add(user)
            created_count += 1
            print(f"✅ Создан пользователь: {email} (роль: {role})")
        else:
            print(f"⏭️ Пользователь {email} уже существует, пропускаем")

    session.commit()
    print(f"📊 Создано пользователей по умолчанию: {created_count}")
    return created_count