import logging
import time

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine

logger = logging.getLogger(__name__)


def wait_for_database(attempts: int = 30, delay_seconds: float = 2.0) -> None:
    for attempt in range(1, attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("Database is ready")
            return
        except SQLAlchemyError as exc:
            if attempt == attempts:
                raise RuntimeError("Database did not become ready") from exc
            logger.info("Waiting for database (%s/%s)", attempt, attempts)
            time.sleep(delay_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    wait_for_database()
