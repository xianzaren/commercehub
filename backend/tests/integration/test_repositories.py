import uuid

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repository import UserRepository


@pytest.mark.integration
def test_user_repository_round_trip(test_engine: Engine) -> None:
    email = f"repository-{uuid.uuid4().hex}@example.com"
    with Session(test_engine) as session, session.begin():
        repository = UserRepository(session)
        created = repository.add(User(email=email, password_hash="not-a-real-hash"))
        assert created.id is not None
        assert repository.get_by_email(email.upper()) is created
