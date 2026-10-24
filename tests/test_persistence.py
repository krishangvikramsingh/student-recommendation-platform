import sqlite3

import pytest

from srp.models import ReviewStatus
from srp.seed import build_sample_platform
from srp.service import Platform
from srp.store import SqliteStore

OPEN = []


def open_store(path):
    store = SqliteStore(path)
    OPEN.append(store)
    return store


@pytest.fixture(autouse=True)
def close_stores():
    yield
    while OPEN:
        OPEN.pop().close()


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "platform.db")


def test_data_survives_restart(db_path):
    platform, college = build_sample_platform(open_store(db_path), require_email_verification=False)
    student = platform.register("Asha Rao", "asha@nmims.edu.in", "secret123", college.college_id)
    admin = platform.find_user("admin@platform.in")
    pg = next(r for r in platform.recommendations.values() if r.category.value == "pg_hostel")
    review = platform.submit_review(student.user_id, pg.rec_id, 5, "Clean rooms")
    platform.validate_review(admin.user_id, review.review_id, True)
    platform.report_review(student.user_id, review.review_id, "testing")
    platform.set_preferences(student.user_id, ["sports"])

    reopened = Platform(store=open_store(db_path))
    assert reopened.find_user("ASHA@nmims.edu.in").preferences == {"sports"}
    again = reopened.reviews[review.review_id]
    assert again.status == ReviewStatus.UNDER_REVIEW and again.reports == {student.user_id: "testing"}
    assert reopened.login("asha@nmims.edu.in", "secret123")
    assert any(n.category == "moderation" for n in reopened.notifications(admin.user_id))
    assert any(e.action == "review_published" for e in reopened.audit_entries(admin.user_id))


def test_ids_do_not_collide_after_restart(db_path):
    platform, college = build_sample_platform(open_store(db_path))
    first = platform.register("Asha Rao", "asha@nmims.edu.in", "secret123", college.college_id)
    reopened = Platform(store=open_store(db_path))
    second = reopened.register("Karan", "karan@nmims.edu.in", "secret456", college.college_id)
    assert second.user_id != first.user_id and len(reopened.users) == 3


def test_lockout_state_is_persisted(db_path):
    platform, college = build_sample_platform(open_store(db_path))
    platform.register("Asha Rao", "asha@nmims.edu.in", "secret123", college.college_id)
    for _ in range(5):
        with pytest.raises(Exception):
            platform.login("asha@nmims.edu.in", "wrong")
    reopened = Platform(store=open_store(db_path))
    with pytest.raises(Exception) as info:
        reopened.login("asha@nmims.edu.in", "secret123")
    assert type(info.value).__name__ == "AccountLocked"


def test_database_rejects_out_of_range_rating(db_path):
    store = open_store(db_path)
    platform, college = build_sample_platform(store)
    student = platform.register("Asha Rao", "asha@nmims.edu.in", "secret123", college.college_id)
    rec = next(iter(platform.recommendations))
    with pytest.raises(sqlite3.IntegrityError):
        store.db.execute(
            "INSERT INTO reviews VALUES ('RVX','%s','%s',9,'x','Pending','2026-01-01T00:00:00',NULL,'')"  # noqa: UP031
            % (student.user_id, rec)
        )


def test_database_rejects_duplicate_email_and_dangling_foreign_key(db_path):
    store = open_store(db_path)
    platform, college = build_sample_platform(store)
    platform.register("Asha Rao", "asha@nmims.edu.in", "secret123", college.college_id)
    with pytest.raises(sqlite3.IntegrityError):
        store.db.execute(
            "INSERT INTO users (user_id,name,email,password_hash,role,college_id,phone,verified,suspended,"
            "failed_attempts,preferences,disabled_notifications) VALUES "
            "('X1','n','asha@nmims.edu.in','h','student','',' ',1,0,0,'[]','[]')"
        )
    with pytest.raises(sqlite3.IntegrityError):
        store.db.execute(
            "INSERT INTO reviews VALUES ('RVY','NOUSER','NOREC',3,'x','Pending','2026-01-01T00:00:00',NULL,'')"
        )


def test_notification_read_status_survives_restart(db_path):
    platform, college = build_sample_platform(open_store(db_path))
    admin = platform.find_user("admin@platform.in")
    student = platform.register("Asha Rao", "asha@nmims.edu.in", "secret123", college.college_id)
    platform.verify_student(admin.user_id, student.user_id)
    note = platform.notifications(student.user_id)[0]
    platform.mark_notification_read(student.user_id, note.notification_id)
    reopened = Platform(store=open_store(db_path))
    assert reopened.notifications(student.user_id)[0].read is True
