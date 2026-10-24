import pytest

from srp.errors import (
    AccountLocked,
    DuplicateAccount,
    DuplicateReport,
    InvalidCollegeEmail,
    InvalidCredentials,
    InvalidReview,
    NotAuthorised,
)
from srp.models import ReviewStatus


def test_valid_college_email_registers_verified_student(world):
    platform, college = world
    user = platform.register("Meera", "meera@nmims.edu.in", "pass1234", college.college_id)
    assert user.verified and user.role == "student"


def test_lookalike_domain_is_rejected(world):
    platform, college = world
    with pytest.raises(InvalidCollegeEmail):
        platform.register("Fake", "fake@notnmims.edu.in", "pass1234", college.college_id)


def test_duplicate_email_is_rejected(world, student):
    platform, college = world
    with pytest.raises(DuplicateAccount):
        platform.register("Asha Again", "asha@nmims.edu.in", "other", college.college_id)


def test_duplicate_email_check_ignores_case(world, student):
    platform, college = world
    with pytest.raises(DuplicateAccount):
        platform.register("Asha Again", "ASHA@nmims.edu.in", "other", college.college_id)


def test_login_with_correct_password(world, student):
    platform, _ = world
    assert platform.login("asha@nmims.edu.in", "secret123").user_id == student.user_id


def test_login_with_wrong_password(world, student):
    platform, _ = world
    with pytest.raises(InvalidCredentials):
        platform.login("asha@nmims.edu.in", "nope")


def test_lock_lifts_after_fifteen_minutes(world, student, clock):
    platform, _ = world
    for _ in range(5):
        with pytest.raises(InvalidCredentials):
            platform.login("asha@nmims.edu.in", "wrong")
    with pytest.raises(AccountLocked):
        platform.login("asha@nmims.edu.in", "secret123")
    clock.advance(minutes=16)
    assert platform.login("asha@nmims.edu.in", "secret123")


def test_suspended_account_cannot_login(world, student, admin):
    platform, _ = world
    platform.suspend_user(admin.user_id, student.user_id)
    with pytest.raises(Exception):
        platform.login("asha@nmims.edu.in", "secret123")


def test_search_is_sorted_by_distance(world):
    platform, _ = world
    platform.add_recommendation("Far Cafe", "restaurant", next(iter(platform.cities)), 19.1200, 72.8500, 1)
    results = platform.search("restaurant", 19.1050, 72.8370)["results"]
    distances = [r["distance_km"] for r in results]
    assert distances == sorted(distances)
    assert len(results) == 2


def test_search_respects_radius(world):
    platform, _ = world
    assert platform.search("sports", 19.1044, 72.8365, radius_km=0.5)["results"] == []
    assert len(platform.search("sports", 19.1044, 72.8365, radius_km=5)["results"]) == 1


def test_empty_search_prompts_to_expand_radius(world):
    platform, _ = world
    outcome = platform.search("event", 19.1044, 72.8365)
    assert outcome["results"] == [] and "expand" in outcome["message"]


def test_price_filter(world):
    platform, _ = world
    assert platform.search("pg_hostel", 19.1044, 72.8365, max_price=1)["results"] == []


def test_rating_filter_uses_published_reviews(world, student, admin):
    platform, _ = world
    pg = next(r for r in platform.recommendations.values() if r.category.value == "pg_hostel")
    review = platform.submit_review(student.user_id, pg.rec_id, 5, "Great")
    platform.validate_review(admin.user_id, review.review_id, True)
    assert len(platform.search("pg_hostel", 19.1044, 72.8365, min_rating=4.5)["results"]) == 1


@pytest.mark.parametrize("rating", [0, 6, -1])
def test_rating_outside_range_is_rejected(world, student, rating):
    platform, _ = world
    rec = next(iter(platform.recommendations.values()))
    with pytest.raises(InvalidReview):
        platform.submit_review(student.user_id, rec.rec_id, rating, "x")


def test_fractional_rating_is_rejected(world, student):
    platform, _ = world
    rec = next(iter(platform.recommendations.values()))
    with pytest.raises(InvalidReview):
        platform.submit_review(student.user_id, rec.rec_id, 4.5, "x")


def test_rejected_review_does_not_count(world, student, admin):
    platform, _ = world
    rec = next(iter(platform.recommendations.values()))
    review = platform.submit_review(student.user_id, rec.rec_id, 1, "Bad")
    platform.validate_review(admin.user_id, review.review_id, False)
    assert review.status == ReviewStatus.REJECTED and rec.average_rating == 0.0


def test_student_cannot_validate_reviews(world, student):
    platform, _ = world
    rec = next(iter(platform.recommendations.values()))
    review = platform.submit_review(student.user_id, rec.rec_id, 3, "ok")
    with pytest.raises(NotAuthorised):
        platform.validate_review(student.user_id, review.review_id, True)


def test_report_moves_review_under_review(world, student, admin):
    platform, _ = world
    rec = next(iter(platform.recommendations.values()))
    review = platform.submit_review(student.user_id, rec.rec_id, 3, "ok")
    platform.validate_review(admin.user_id, review.review_id, True)
    platform.report_review(student.user_id, review.review_id, "fake")
    assert review.status == ReviewStatus.UNDER_REVIEW


def test_same_user_cannot_report_twice(world, student):
    platform, _ = world
    rec = next(iter(platform.recommendations.values()))
    review = platform.submit_review(student.user_id, rec.rec_id, 3, "ok")
    platform.report_review(student.user_id, review.review_id, "fake")
    with pytest.raises(DuplicateReport):
        platform.report_review(student.user_id, review.review_id, "fake")


def test_recommendations_follow_preferences(world, student):
    platform, _ = world
    student.preferences = {"sports"}
    names = [r.name for r in platform.recommend(student.user_id, 19.1044, 72.8365)]
    assert names == ["Juhu Sports Club"]
