from sqlalchemy import func, select

from app.models import SmokeTest


def count_rows(session) -> int:
    return session.scalar(select(func.count()).select_from(SmokeTest))


def test_rows_written_in_a_test_are_visible_inside_it(db_session):
    db_session.add(SmokeTest(note="hello"))
    db_session.commit()

    assert count_rows(db_session) == 1


def test_each_test_starts_with_a_clean_database(db_session):
    assert count_rows(db_session) == 0
