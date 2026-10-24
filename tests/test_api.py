import http.client
import json
import threading
from datetime import datetime, timedelta

import pytest
import requests

from srp.seed import build_sample_platform, load_demo_data
from srp.server import create_server

ADMIN_PASSWORD = "admin-pass"


@pytest.fixture
def app():
    platform, college = build_sample_platform(admin_password=ADMIN_PASSWORD)
    load_demo_data(platform)
    platform.require_email_verification = False  # legacy suites predate email confirmation; see test_auth.py
    server = create_server(platform, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    yield type("App", (), {"url": f"http://{host}:{port}", "platform": platform, "college": college, "server": server})
    server.shutdown()
    server.server_close()


def register_and_login(app, email="asha@nmims.edu.in", password="secret123"):
    body = {"name": "Asha Rao", "email": email, "password": password, "college_id": app.college.college_id}
    assert requests.post(app.url + "/register", json=body).status_code == 201
    token = requests.post(app.url + "/login", json={"email": email, "password": password}).json()["token"]
    return {"Authorization": "Bearer " + token}


def admin_headers(app):
    token = requests.post(app.url + "/login", json={"email": "admin@platform.in", "password": ADMIN_PASSWORD}).json()[
        "token"
    ]
    return {"Authorization": "Bearer " + token}


def pg_id(app):
    results = requests.get(app.url + "/search", params={"category": "pg_hostel", "lat": 19.1044, "lon": 72.8365}).json()
    return results["results"][0]["id"]


def test_health_and_colleges(app):
    assert requests.get(app.url + "/health").json() == {"status": "ok"}
    assert requests.get(app.url + "/colleges").json()[0]["name"] == "NMIMS MPSTME"


def test_register_status_codes(app):
    cid = app.college.college_id
    ok = requests.post(
        app.url + "/register", json={"name": "A", "email": "a@nmims.edu.in", "password": "secret123", "college_id": cid}
    )
    assert ok.status_code == 201 and ok.json()["verified"] is True
    assert (
        requests.post(
            app.url + "/register",
            json={"name": "B", "email": "b@gmail.com", "password": "secret123", "college_id": cid},
        ).status_code
        == 422
    )
    assert (
        requests.post(
            app.url + "/register",
            json={"name": "A", "email": "A@NMIMS.edu.in", "password": "secret123", "college_id": cid},
        ).status_code
        == 409
    )
    assert requests.post(app.url + "/register", json={"name": "C"}).status_code == 422


def test_login_failure_and_lockout(app):
    register_and_login(app)
    for _ in range(5):
        assert (
            requests.post(app.url + "/login", json={"email": "asha@nmims.edu.in", "password": "bad"}).status_code == 401
        )
    locked = requests.post(app.url + "/login", json={"email": "asha@nmims.edu.in", "password": "secret123"})
    assert locked.status_code == 423 and "15 minutes" in locked.json()["message"]


def test_protected_routes_need_login(app):
    assert requests.post(app.url + "/reviews", json={}).status_code == 401
    assert requests.get(app.url + "/notifications").status_code == 401
    assert requests.get(app.url + "/admin/audit").status_code == 401


def test_student_cannot_reach_admin_functions(app):
    headers = register_and_login(app)
    assert requests.get(app.url + "/admin/reviews", headers=headers).status_code == 403
    assert requests.get(app.url + "/admin/users", headers=headers).status_code == 403
    assert (
        requests.post(app.url + "/admin/cities", json={"name": "X", "state": "Y"}, headers=headers).status_code == 403
    )
    assert (
        requests.post(app.url + "/reviews/RV0001/validate", json={"approve": True}, headers=headers).status_code == 403
    )


def test_review_flow_updates_search_rating(app):
    headers = register_and_login(app)
    rec = pg_id(app)
    created = requests.post(app.url + "/reviews", json={"rec_id": rec, "rating": 4, "comment": "Good"}, headers=headers)
    assert created.status_code == 201 and created.json()["status"] == "Pending"
    admin = admin_headers(app)
    queue = requests.get(app.url + "/admin/reviews", headers=admin).json()
    assert queue[0]["comment"] == "Good"
    done = requests.post(
        f"{app.url}/reviews/{created.json()['review_id']}/validate", json={"approve": True}, headers=admin
    )
    assert done.json()["status"] == "Published"
    found = requests.get(app.url + "/search", params={"category": "pg_hostel", "lat": 19.1044, "lon": 72.8365}).json()
    assert found["results"][0]["rating"] == 4.0 and found["results"][0]["review_count"] == 1


def test_invalid_ratings_return_422(app):
    headers = register_and_login(app)
    rec = pg_id(app)
    for rating in (4.5, 0, 6, True, "5"):
        response = requests.post(
            app.url + "/reviews", json={"rec_id": rec, "rating": rating, "comment": "x"}, headers=headers
        )
        assert response.status_code == 422


def test_report_flow(app):
    headers = register_and_login(app)
    rec = pg_id(app)
    review = requests.post(
        app.url + "/reviews", json={"rec_id": rec, "rating": 3, "comment": "ok"}, headers=headers
    ).json()
    admin = admin_headers(app)
    requests.post(f"{app.url}/reviews/{review['review_id']}/validate", json={"approve": True}, headers=admin)
    first = requests.post(f"{app.url}/reviews/{review['review_id']}/report", json={"reason": "fake"}, headers=headers)
    again = requests.post(f"{app.url}/reviews/{review['review_id']}/report", json={"reason": "fake"}, headers=headers)
    assert first.json()["status"] == "Under Review" and again.status_code == 409


def test_search_validation_and_empty_message(app):
    assert requests.get(app.url + "/search", params={"category": "pg_hostel"}).status_code == 422
    assert requests.get(app.url + "/search", params={"category": "spa", "lat": 1, "lon": 1}).status_code == 422
    empty = requests.get(app.url + "/search", params={"category": "pg_hostel", "lat": 28.6, "lon": 77.2}).json()
    assert empty["results"] == [] and "expand" in empty["message"]


def test_events_endpoint_is_chronological(app):
    dates = [e["event_date"] for e in requests.get(app.url + "/events").json()["results"]]
    assert dates == sorted(dates) and len(dates) == 3
    sports = requests.get(app.url + "/events", params={"event_type": "Sports"}).json()["results"]
    assert [e["name"] for e in sports] == ["Inter-College Football Cup"]


def test_public_responses_never_expose_private_details(app):
    headers = register_and_login(app)
    rec = pg_id(app)
    review = requests.post(
        app.url + "/reviews", json={"rec_id": rec, "rating": 5, "comment": "Great"}, headers=headers
    ).json()
    requests.post(
        f"{app.url}/reviews/{review['review_id']}/validate", json={"approve": True}, headers=admin_headers(app)
    )
    public = [
        requests.get(app.url + "/listings/" + rec).text,
        requests.get(app.url + "/search", params={"category": "pg_hostel", "lat": 19.1044, "lon": 72.8365}).text,
        requests.get(app.url + "/colleges").text,
        requests.get(app.url + "/events").text,
    ]
    for body in public:
        assert "asha@" not in body and "password" not in body and "nmims.edu.in" not in body
    assert "Asha Rao" in public[0]


def test_admin_user_list_masks_email(app):
    register_and_login(app)
    users = requests.get(app.url + "/admin/users", headers=admin_headers(app)).json()
    assert users[0]["email"] == "a***@nmims.edu.in"


def test_logout_invalidates_token(app):
    headers = register_and_login(app)
    assert requests.get(app.url + "/me", headers=headers).status_code == 200
    requests.post(app.url + "/logout", headers=headers)
    assert requests.get(app.url + "/me", headers=headers).status_code == 401


def test_idle_session_expires(app):
    headers = register_and_login(app)
    now = datetime.now()
    app.server.sessions.clock = lambda: now + timedelta(minutes=31)
    assert requests.get(app.url + "/me", headers=headers).status_code == 401


def test_suspending_a_user_ends_their_session(app):
    headers = register_and_login(app)
    student_id = requests.get(app.url + "/me", headers=headers).json()["id"]
    requests.post(f"{app.url}/admin/users/{student_id}/suspend", json={}, headers=admin_headers(app))
    assert requests.get(app.url + "/me", headers=headers).status_code == 401
    relogin = requests.post(app.url + "/login", json={"email": "asha@nmims.edu.in", "password": "secret123"})
    assert relogin.status_code == 403


def test_notifications_and_settings_endpoints(app):
    headers = register_and_login(app)
    admin = admin_headers(app)
    city = requests.get(app.url + "/cities").json()[0]["id"]
    body = {
        "name": "Quiz Night",
        "category": "event",
        "city_id": city,
        "lat": 19.1,
        "lon": 72.8,
        "event_date": (datetime.now() + timedelta(days=2)).date().isoformat(),
        "details": {"event_type": "Cultural"},
    }
    assert requests.post(app.url + "/admin/listings", json=body, headers=admin).status_code == 201
    notes = requests.get(app.url + "/notifications", headers=headers).json()
    assert notes[0]["read"] is False and "Quiz Night" in notes[0]["message"]
    assert requests.post(f"{app.url}/notifications/{notes[0]['id']}/read", headers=headers).json()["read"] is True
    assert (
        requests.put(app.url + "/me/notification-settings", json={"disabled": ["event"]}, headers=headers).status_code
        == 200
    )
    requests.post(app.url + "/admin/listings", json={**body, "name": "Another"}, headers=admin)
    assert len(requests.get(app.url + "/notifications", headers=headers).json()) == 1


def test_admin_audit_endpoint(app):
    register_and_login(app)
    entries = requests.get(app.url + "/admin/audit", headers=admin_headers(app)).json()
    assert any(e["action"] == "register" for e in entries)


def test_malformed_and_unknown_requests(app):
    assert (
        requests.post(app.url + "/login", data="{not json", headers={"Content-Type": "application/json"}).status_code
        == 400
    )
    assert requests.post(app.url + "/login", json=["list"]).status_code == 422
    assert requests.get(app.url + "/nope/nothing").status_code == 404
    assert requests.post(app.url + "/nothing", json={}).status_code == 404


def test_oversized_body_is_rejected(app):
    response = requests.post(app.url + "/login", data="x" * 70000, headers={"Content-Type": "application/json"})
    assert response.status_code == 422


def test_static_pages_and_headers(app):
    page = requests.get(app.url + "/")
    assert page.status_code == 200 and "Student Recommendation Platform" in page.text
    assert (
        page.headers["X-Content-Type-Options"] == "nosniff"
        and "default-src 'self'" in page.headers["Content-Security-Policy"]
    )
    assert requests.get(app.url + "/app.js").status_code == 200


def test_path_traversal_is_blocked(app):
    host, port = app.server.server_address
    conn = http.client.HTTPConnection(host, port)
    conn.request("GET", "/../service.py")
    response = conn.getresponse()
    assert response.status == 404 and b"import" not in response.read()
    conn.close()


def test_errors_do_not_leak_internals(app):
    body = requests.post(
        app.url + "/register",
        json={"name": "x", "email": "x@gmail.com", "password": "secret123", "college_id": app.college.college_id},
    ).text
    assert "Traceback" not in body and "srp/" not in body
    assert json.loads(body)["error"] == "InvalidCollegeEmail"
