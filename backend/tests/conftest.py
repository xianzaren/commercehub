from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.db.session import build_engine


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    settings = get_settings()
    target = make_url(settings.test_database_url)
    if not target.database or not target.database.endswith("_test"):
        raise RuntimeError("Refusing to reset a database without the _test suffix")
    config = Config("alembic.ini")
    config.attributes["database_url"] = settings.test_database_url
    # Test data may contain multiple SKUs per product, which cannot be represented
    # by older migrations. Recreate only the validated disposable schema instead
    # of downgrading its data. This also recovers a previous interrupted test reset.
    engine = build_engine(settings.test_database_url)
    with engine.connect() as connection:
        tables = inspect(connection).get_table_names()
        quote = connection.dialect.identifier_preparer.quote
        connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS=0")
        try:
            for table in tables:
                connection.exec_driver_sql(f"DROP TABLE {quote(table)}")
            connection.commit()
        finally:
            connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS=1")
            connection.commit()
    command.upgrade(config, "head")
    yield engine
    engine.dispose()
