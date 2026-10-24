import pytest

from srp.errors import AccountLocked, InvalidCollegeEmail, NotVerified
from srp.models import ReviewStatus


def test_tc01_registration_rejects_non_college_email(world):
    platform, college = world
    with pytest.raises(InvalidCollegeEmail):
        platform.register("Rahul", "rahul@gmail.com", "pass1234", college.college_id)
    assert platform.find_user("rahul@gmail.com") is None


def test_tc02_account_locks_after_five_failed_logins(world, student):
    platform, _ = world
    for _ in range(5):
        with pytest.raises(Exception):
            platform.login("asha@nmims.edu.in", "wrong")
    with pytest.raises(AccountLocked):
        platform.login("asha@nmims.edu.in", "secret123")


def test_tc03_unverified_student_cannot_submit_review(world, unverified):
    platform, _ = world
    rec = next(iter(platform.recommendations.values()))
    with pytest.raises(NotVerified):
        platform.submit_review(unverified.user_id, rec.rec_id, 4, "Nice place")
    assert platform.reviews == {}


def test_tc04_validated_reviews_update_rating_shown_in_search(world, student, admin):
    platform, college = world
    pg = next(r for r in platform.recommendations.values() if r.category.value == "pg_hostel")
    other = platform.register("Karan", "karan@nmims.edu.in", "secret456", college.college_id)
    first = platform.submit_review(student.user_id, pg.rec_id, 4, "Clean rooms")
    second = platform.submit_review(other.user_id, pg.rec_id, 5, "Good food")
    assert first.status == ReviewStatus.PENDING
    platform.validate_review(admin.user_id, first.review_id, True)
    platform.validate_review(admin.user_id, second.review_id, True)
    shown = platform.search("pg_hostel", 19.1044, 72.8365)["results"][0]["rec"]
    assert shown.average_rating == 4.5
