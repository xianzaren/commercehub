from collections.abc import Iterator

import pytest
from sqlalchemy import Engine

from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.db.session import build_engine


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    settings = get_settings()
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", settings.test_database_url.replace("%", "%%"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = build_engine(settings.test_database_url)
    yield engine
    engine.dispose()
