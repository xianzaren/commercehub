from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def lock(self, user_id: int) -> User | None:
        statement = select(User).where(User.id == user_id).with_for_update()
        return self.session.scalar(statement)

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email.strip().lower())
        return self.session.scalar(statement)

    def add(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()
        return user

    def exists_by_email(self, email: str) -> bool:
        statement = select(User.id).where(User.email == email.strip().lower()).limit(1)
        return self.session.scalar(statement) is not None
