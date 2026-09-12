import pytest
from pydantic import ValidationError

from app.schemas.pagination import PageParams


def test_page_offset() -> None:
    assert PageParams(page=3, page_size=25).offset == 50


@pytest.mark.parametrize(
    ("page", "page_size"),
    [(0, 20), (1, 0), (1, 101)],
)
def test_invalid_page_params(page: int, page_size: int) -> None:
    with pytest.raises(ValidationError):
        PageParams(page=page, page_size=page_size)
