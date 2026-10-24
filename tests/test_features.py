from datetime import timedelta

import pytest

from srp.errors import AccountSuspended, DuplicateReview, InvalidInput, InvalidReview, NotAuthorised, NotFound
from srp.models import ReviewStatus
from srp.security import hash_password, verify_password


def first_rec(platform, category="pg_hostel"):
    return next(r for r in platform.recommendations.values() if r.category.value == category)


def test_passwords_are_salted_and_verifiable():
    first, second = hash_password("secret123"), hash_password("secret123")
    assert first != second and "secret123" not in first
    assert verify_password("secret123", first) and not verify_password("secret124", first)


def test_stored_password_is_not_plaintext(world, student):
    assert "secret123" not in student.password_hash and student.password_hash.startswith("scrypt$")


def test_short_password_is_rejected(world):
    platform, college = world
    with pytest.raises(InvalidInput):
        platform.register("Short", "short@nmims.edu.in", "abc", college.college_id)


def test_subdomain_of_college_domain_is_accepted(world):
    platform, college = world
    user = platform.register("Sub", "sub@mail.nmims.edu.in", "pass1234", college.college_id)
    assert user.verified


def test_unknown_email_cannot_login(world):
    platform, _ = world
    with pytest.raises(Exception) as info:
        platform.login("nobody@nmims.edu.in", "whatever1")
    assert type(info.value).__name__ == "InvalidCredentials"


def test_lockout_is_recorded_in_audit_log(world, student, admin):
    platform, _ = world
    for _ in range(5):
        with pytest.raises(Exception):
            platform.login("asha@nmims.edu.in", "wrong")
    actions = [e.action for e in platform.audit_entries(admin.user_id)]
    assert actions.count("login_failed") == 5


def test_empty_comment_is_rejected(world, student):
    platform, _ = world
    with pytest.raises(InvalidReview):
        platform.submit_review(student.user_id, first_rec(platform).rec_id, 4, "   ")


def test_boolean_rating_is_rejected(world, student):
    platform, _ = world
    with pytest.raises(InvalidReview):
        platform.submit_review(student.user_id, first_rec(platform).rec_id, True, "fine")


def test_spam_and_profanity_are_rejected(world, student):
    platform, _ = world
    rec = first_rec(platform)
    for text in ("Visit http://spam.example now", "aaaaaaaaaaaaaaaa", "this is shit"):
        with pytest.raises(InvalidReview):
            platform.submit_review(student.user_id, rec.rec_id, 3, text)


def test_review_on_unknown_listing_is_rejected(world, student):
    platform, _ = world
    with pytest.raises(NotFound):
        platform.submit_review(student.user_id, "RC9999", 3, "ok")


def test_duplicate_review_for_same_listing_is_rejected(world, student):
    platform, _ = world
    rec = first_rec(platform)
    platform.submit_review(student.user_id, rec.rec_id, 3, "ok")
    with pytest.raises(DuplicateReview):
        platform.submit_review(student.user_id, rec.rec_id, 4, "again")


def test_suspended_user_cannot_submit_review(world, student, admin):
    platform, _ = world
    platform.suspend_user(admin.user_id, student.user_id)
    with pytest.raises(AccountSuspended):
        platform.submit_review(student.user_id, first_rec(platform).rec_id, 3, "ok")


def test_pending_review_does_not_change_rating(world, student):
    platform, _ = world
    rec = first_rec(platform)
    platform.submit_review(student.user_id, rec.rec_id, 5, "great")
    assert rec.average_rating == 0.0


def test_reported_review_is_removed_from_average_until_resolved(world, student, admin):
    platform, college = world
    other = platform.register("Karan", "karan@nmims.edu.in", "secret456", college.college_id)
    rec = first_rec(platform)
    first = platform.submit_review(student.user_id, rec.rec_id, 5, "great")
    second = platform.submit_review(other.user_id, rec.rec_id, 1, "bad")
    for review in (first, second):
        platform.validate_review(admin.user_id, review.review_id, True)
    assert rec.average_rating == 3.0
    platform.report_review(student.user_id, second.review_id, "looks fake")
    assert rec.average_rating == 5.0
    platform.validate_review(admin.user_id, second.review_id, True)
    assert rec.average_rating == 3.0


def test_report_requires_reason(world, student):
    platform, _ = world
    review = platform.submit_review(student.user_id, first_rec(platform).rec_id, 3, "ok")
    with pytest.raises(InvalidInput):
        platform.report_review(student.user_id, review.review_id, "  ")


def test_moderation_outcome_notifies_author_and_reporter(world, student, admin):
    platform, college = world
    reporter = platform.register("Karan", "karan@nmims.edu.in", "secret456", college.college_id)
    review = platform.submit_review(student.user_id, first_rec(platform).rec_id, 2, "meh")
    platform.report_review(reporter.user_id, review.review_id, "unfair")
    platform.validate_review(admin.user_id, review.review_id, False)
    assert "rejected" in platform.notifications(student.user_id)[0].message
    assert "removed" in platform.notifications(reporter.user_id)[0].message
    assert review.status == ReviewStatus.REJECTED


def test_report_notifies_administrators(world, student, admin):
    platform, _ = world
    review = platform.submit_review(student.user_id, first_rec(platform).rec_id, 2, "meh")
    platform.report_review(student.user_id, review.review_id, "spammy")
    assert any("reported" in n.message for n in platform.notifications(admin.user_id))


def test_moderation_queue_lists_pending_and_reported(world, student, admin):
    platform, _ = world
    review = platform.submit_review(student.user_id, first_rec(platform).rec_id, 4, "nice")
    assert [r.review_id for r in platform.moderation_queue(admin.user_id)] == [review.review_id]
    platform.validate_review(admin.user_id, review.review_id, True)
    assert platform.moderation_queue(admin.user_id) == []


@pytest.mark.parametrize("action", ["moderation_queue", "list_students", "audit_entries"])
def test_students_cannot_use_admin_reads(world, student, action):
    platform, _ = world
    with pytest.raises(NotAuthorised):
        getattr(platform, action)(student.user_id)


def test_students_cannot_manage_catalogue(world, student):
    platform, _ = world
    city = next(iter(platform.cities))
    with pytest.raises(NotAuthorised):
        platform.create_city(student.user_id, "Pune", "Maharashtra")
    with pytest.raises(NotAuthorised):
        platform.create_college(student.user_id, "X", "x.edu", city)
    with pytest.raises(NotAuthorised):
        platform.create_recommendation(student.user_id, "X", "restaurant", city, 19.1, 72.8)
    with pytest.raises(NotAuthorised):
        platform.delete_recommendation(student.user_id, first_rec(platform).rec_id)
    with pytest.raises(NotAuthorised):
        platform.suspend_user(student.user_id, student.user_id)


def test_admin_manages_cities_colleges_and_listings(world, admin):
    platform, _ = world
    city = platform.create_city(admin.user_id, "Pune", "Maharashtra")
    college = platform.create_college(admin.user_id, "Sample College", "sample.edu.in", city.city_id, "FC Road")
    platform.update_city(admin.user_id, city.city_id, name="Pune City")
    platform.update_college(admin.user_id, college.college_id, address="JM Road")
    rec = platform.create_recommendation(
        admin.user_id, "Cafe Pune", "restaurant", city.city_id, 18.52, 73.85, 1, details={"cuisine_type": "Cafe"}
    )
    platform.update_recommendation(admin.user_id, rec.rec_id, name="Cafe Pune 2", price_level=2)
    assert platform.cities[city.city_id].name == "Pune City"
    assert platform.colleges[college.college_id].address == "JM Road"
    assert platform.recommendations[rec.rec_id].name == "Cafe Pune 2"
    actions = {e.action for e in platform.audit_entries(admin.user_id)}
    assert {"city_created", "college_created", "listing_created", "listing_updated"} <= actions


def test_duplicate_college_domain_is_rejected(world, admin):
    platform, _ = world
    city = next(iter(platform.cities))
    with pytest.raises(InvalidInput):
        platform.create_college(admin.user_id, "Clone", "nmims.edu.in", city)


def test_listing_details_must_match_category(world, admin):
    platform, _ = world
    city = next(iter(platform.cities))
    with pytest.raises(InvalidInput):
        platform.create_recommendation(
            admin.user_id, "Bad", "restaurant", city, 19.1, 72.8, details={"rent_range": "1"}
        )


def test_invalid_coordinates_and_price_are_rejected(world, admin):
    platform, _ = world
    city = next(iter(platform.cities))
    with pytest.raises(InvalidInput):
        platform.create_recommendation(admin.user_id, "Bad", "restaurant", city, 123.0, 72.8)
    with pytest.raises(InvalidInput):
        platform.create_recommendation(admin.user_id, "Bad", "restaurant", city, 19.1, 72.8, price_level=7)


def test_archived_listing_leaves_search_but_keeps_reviews(world, student, admin):
    platform, _ = world
    rec = first_rec(platform)
    review = platform.submit_review(student.user_id, rec.rec_id, 4, "nice")
    platform.delete_recommendation(admin.user_id, rec.rec_id)
    assert platform.search("pg_hostel", 19.1044, 72.8365)["results"] == []
    assert review.review_id in platform.reviews


def test_reinstated_user_can_login_again(world, student, admin):
    platform, _ = world
    platform.suspend_user(admin.user_id, student.user_id)
    platform.reinstate_user(admin.user_id, student.user_id)
    assert platform.login("asha@nmims.edu.in", "secret123")


def test_admin_cannot_be_suspended(world, admin):
    platform, _ = world
    with pytest.raises(InvalidInput):
        platform.suspend_user(admin.user_id, admin.user_id)


def test_admin_can_verify_unverified_student(world, unverified, admin):
    platform, _ = world
    platform.verify_student(admin.user_id, unverified.user_id)
    assert unverified.verified


def test_search_result_counts_only_published_reviews(world, student, admin):
    platform, _ = world
    rec = first_rec(platform)
    review = platform.submit_review(student.user_id, rec.rec_id, 4, "nice")
    assert platform.search("pg_hostel", 19.1044, 72.8365)["results"][0]["review_count"] == 0
    platform.validate_review(admin.user_id, review.review_id, True)
    assert platform.search("pg_hostel", 19.1044, 72.8365)["results"][0]["review_count"] == 1


def test_search_boundary_radius_and_invalid_input(world):
    platform, _ = world
    with pytest.raises(InvalidInput):
        platform.search("restaurant", 19.1, 72.8, radius_km=-1)
    with pytest.raises(InvalidInput):
        platform.search("spa", 19.1, 72.8)
    with pytest.raises(InvalidInput):
        platform.search("restaurant", 95, 72.8)


def test_filters_apply_together(world):
    platform, _ = world
    found = platform.search("restaurant", 19.1050, 72.8370, radius_km=1, max_price=1, min_rating=0)
    assert [i["rec"].name for i in found["results"]] == ["Campus Canteen"]
    none = platform.search("restaurant", 19.1050, 72.8370, radius_km=1, max_price=1, min_rating=3)
    assert none["results"] == []


def add_event(platform, admin, name, days, kind):
    city = next(iter(platform.cities))
    return platform.create_recommendation(
        admin.user_id,
        name,
        "event",
        city,
        19.1044,
        72.8365,
        0,
        details={"event_type": kind},
        event_date=platform.clock().date() + timedelta(days=days),
    )


def test_events_are_listed_chronologically_and_hide_past(world, admin):
    platform, _ = world
    add_event(platform, admin, "Later", 10, "Sports")
    add_event(platform, admin, "Sooner", 2, "Cultural")
    platform.add_recommendation(
        "Old", "event", next(iter(platform.cities)), 19.1, 72.8, event_date=platform.clock().date() - timedelta(days=1)
    )
    assert [e.name for e in platform.list_events()] == ["Sooner", "Later"]


def test_event_filters_by_type_and_date(world, admin):
    platform, _ = world
    add_event(platform, admin, "Match", 5, "Sports")
    add_event(platform, admin, "Show", 6, "Cultural")
    assert [e.name for e in platform.list_events(event_type="sports")] == ["Match"]
    start = (platform.clock().date() + timedelta(days=6)).isoformat()
    assert [e.name for e in platform.list_events(date_from=start)] == ["Show"]


def test_event_requires_date(world, admin):
    platform, _ = world
    with pytest.raises(InvalidInput):
        platform.create_recommendation(admin.user_id, "No date", "event", next(iter(platform.cities)), 19.1, 72.8)


def test_new_event_notifies_matching_students_only(world, student, admin):
    platform, college = world
    sports_fan = platform.register("Karan", "karan@nmims.edu.in", "secret456", college.college_id)
    platform.set_preferences(sports_fan.user_id, ["sports"])
    add_event(platform, admin, "Quiz Night", 4, "Cultural")
    assert len(platform.notifications(student.user_id)) == 1
    assert platform.notifications(sports_fan.user_id) == []


def test_disabled_notification_category_is_respected(world, student, admin):
    platform, _ = world
    platform.set_notification_settings(student.user_id, ["event"])
    add_event(platform, admin, "Quiz Night", 4, "Cultural")
    assert platform.notifications(student.user_id) == []


def test_read_status_is_updated(world, student, admin):
    platform, _ = world
    add_event(platform, admin, "Quiz Night", 4, "Cultural")
    note = platform.notifications(student.user_id)[0]
    assert not note.read
    platform.mark_notification_read(student.user_id, note.notification_id)
    assert platform.notifications(student.user_id)[0].read


def test_user_cannot_mark_someone_elses_notification(world, student, admin):
    platform, college = world
    other = platform.register("Karan", "karan@nmims.edu.in", "secret456", college.college_id)
    add_event(platform, admin, "Quiz Night", 4, "Cultural")
    note = platform.notifications(student.user_id)[0]
    with pytest.raises(NotFound):
        platform.mark_notification_read(other.user_id, note.notification_id)


def test_updated_preferences_apply_immediately(world, student):
    platform, _ = world
    platform.set_preferences(student.user_id, ["sports"])
    assert [r.name for r in platform.recommend(student.user_id, 19.1044, 72.8365)] == ["Juhu Sports Club"]
    platform.set_preferences(student.user_id, ["restaurant"])
    assert [r.name for r in platform.recommend(student.user_id, 19.1044, 72.8365)] == ["Campus Canteen"]


def test_invalid_preferences_are_rejected(world, student):
    platform, _ = world
    with pytest.raises(InvalidInput):
        platform.set_preferences(student.user_id, ["spa"])
