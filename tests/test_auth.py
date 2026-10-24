import threading
from urllib.parse import parse_qs, urlparse

import pytest
import requests

from srp.errors import EmailNotVerified, InvalidCredentials, InvalidInput, InvalidToken
from srp.mailer import ConsoleMailer
from srp.ratelimit import RateLimiter
from srp.seed import build_sample_platform
from srp.server import create_server
from srp.service import Platform
from srp.store import SqliteStore

ADMIN = "admin-pass"
CSRF = {"X-Requested-With": "srp"}


@pytest.fixture
def secure_world(clock):
    platform, college = build_sample_platform(admin_password=ADMIN)
    platform.clock = clock
    return platform, college


def token_from(link):
    return parse_qs(urlparse(link).query).get("verify", parse_qs(urlparse(link).query).get("reset"))[0]


# ---- service layer -------------------------------------------------------------------------------------------


def test_registration_is_unverified_until_email_confirmed(secure_world):
    platform, college = secure_world
    user = platform.register("Asha", "asha@nmims.edu.in", "secret123", college.college_id)
    assert not user.verified
    with pytest.raises(EmailNotVerified):
        platform.login("asha@nmims.edu.in", "secret123")
    _, raw = platform.verification_token("asha@nmims.edu.in")
    assert platform.confirm_email(raw).verified
    assert platform.login("asha@nmims.edu.in", "secret123") is user


def test_wrong_password_never_reveals_unconfirmed_state(secure_world):
    platform, college = secure_world
    platform.register("Asha", "asha@nmims.edu.in", "secret123", college.college_id)
    with pytest.raises(InvalidCredentials):
        platform.login("asha@nmims.edu.in", "wrong-password")


def test_verification_token_is_single_use_and_expires(secure_world, clock):
    platform, college = secure_world
    platform.register("Asha", "asha@nmims.edu.in", "secret123", college.college_id)
    _, raw = platform.verification_token("asha@nmims.edu.in")
    platform.confirm_email(raw)
    with pytest.raises(InvalidToken):
        platform.confirm_email(raw)
    platform.register("Karan", "karan@nmims.edu.in", "secret456", college.college_id)
    _, late = platform.verification_token("karan@nmims.edu.in")
    clock.advance(hours=25)
    with pytest.raises(InvalidToken):
        platform.confirm_email(late)


def test_new_token_invalidates_the_previous_one(secure_world):
    platform, college = secure_world
    platform.register("Asha", "asha@nmims.edu.in", "secret123", college.college_id)
    _, first = platform.verification_token("asha@nmims.edu.in")
    _, second = platform.verification_token("asha@nmims.edu.in")
    with pytest.raises(InvalidToken):
        platform.confirm_email(first)
    platform.confirm_email(second)


def test_tokens_are_stored_hashed(secure_world):
    platform, college = secure_world
    platform.register("Asha", "asha@nmims.edu.in", "secret123", college.college_id)
    _, raw = platform.verification_token("asha@nmims.edu.in")
    assert raw not in platform.auth_tokens and all(raw not in h for h in platform.auth_tokens)


def test_no_token_for_unknown_or_already_verified_accounts(secure_world, world):
    platform, college = secure_world
    assert platform.verification_token("nobody@nmims.edu.in") is None
    assert platform.reset_token("nobody@nmims.edu.in") is None
    assert platform.verification_token("admin@platform.in") is None


def test_password_reset_flow(secure_world, clock):
    platform, college = secure_world
    platform.register("Asha", "asha@nmims.edu.in", "secret123", college.college_id)
    user, raw = platform.reset_token("asha@nmims.edu.in")
    platform.reset_password(raw, "brand-new-pass")
    assert user.verified  # the reset link proves mailbox ownership
    assert platform.login("asha@nmims.edu.in", "brand-new-pass") is user
    with pytest.raises(InvalidCredentials):
        platform.login("asha@nmims.edu.in", "secret123")
    with pytest.raises(InvalidToken):
        platform.reset_password(raw, "another-pass-1")


def test_reset_unlocks_a_locked_account(secure_world):
    platform, college = secure_world
    platform.register("Asha", "asha@nmims.edu.in", "secret123", college.college_id)
    platform.confirm_email(platform.verification_token("asha@nmims.edu.in")[1])
    for _ in range(5):
        with pytest.raises(InvalidCredentials):
            platform.login("asha@nmims.edu.in", "nope-nope")
    _, raw = platform.reset_token("asha@nmims.edu.in")
    platform.reset_password(raw, "fresh-secret-9")
    assert platform.login("asha@nmims.edu.in", "fresh-secret-9")


def test_weak_reset_password_does_not_burn_the_link(secure_world):
    platform, college = secure_world
    platform.register("Asha", "asha@nmims.edu.in", "secret123", college.college_id)
    _, raw = platform.reset_token("asha@nmims.edu.in")
    with pytest.raises(InvalidInput):
        platform.reset_password(raw, "short")
    platform.reset_password(raw, "long-enough-1")


def test_reset_token_expires_after_an_hour(secure_world, clock):
    platform, college = secure_world
    platform.register("Asha", "asha@nmims.edu.in", "secret123", college.college_id)
    _, raw = platform.reset_token("asha@nmims.edu.in")
    clock.advance(minutes=61)
    with pytest.raises(InvalidToken):
        platform.reset_password(raw, "long-enough-1")


def test_a_verify_token_cannot_reset_a_password(secure_world):
    platform, college = secure_world
    platform.register("Asha", "asha@nmims.edu.in", "secret123", college.college_id)
    _, raw = platform.verification_token("asha@nmims.edu.in")
    with pytest.raises(InvalidToken):
        platform.reset_password(raw, "long-enough-1")


def test_password_policy(secure_world):
    platform, college = secure_world
    for bad in ("short", "x" * 129, "asha@nmims.edu.in"):
        with pytest.raises(InvalidInput):
            platform.register("Asha", "asha@nmims.edu.in", bad, college.college_id)


def test_change_password_requires_current_password(world, student):
    platform, _ = world
    with pytest.raises(InvalidCredentials):
        platform.change_password(student.user_id, "not-it", "new-secret-1")
    platform.change_password(student.user_id, "secret123", "new-secret-1")
    assert platform.login("asha@nmims.edu.in", "new-secret-1")


def test_tokens_survive_restart(tmp_path, clock):
    path = str(tmp_path / "t.db")
    store = SqliteStore(path)
    platform, college = build_sample_platform(store, admin_password=ADMIN)
    platform.clock = clock
    platform.register("Asha", "asha@nmims.edu.in", "secret123", college.college_id)
    _, raw = platform.verification_token("asha@nmims.edu.in")
    store.close()
    store = SqliteStore(path)
    reopened = Platform(clock=clock, store=store)
    assert reopened.confirm_email(raw).verified
    store.close()


def test_rate_limiter_window():
    now = [0.0]
    limiter = RateLimiter(clock=lambda: now[0])
    for _ in range(3):
        limiter.check("k", 3, 60)
    from srp.errors import RateLimited

    with pytest.raises(RateLimited) as err:
        limiter.check("k", 3, 60)
    assert 1 <= err.value.retry_after <= 61
    now[0] = 61
    limiter.check("k", 3, 60)


# ---- HTTP layer ----------------------------------------------------------------------------------------------


@pytest.fixture
def api(clock):
    platform, college = build_sample_platform(admin_password=ADMIN)
    mailer = ConsoleMailer()
    limiter = RateLimiter()
    server = create_server(platform, "127.0.0.1", 0, mailer=mailer, limiter=limiter, dev_links=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    host, port = server.server_address
    yield type(
        "Api",
        (),
        {
            "url": f"http://{host}:{port}",
            "platform": platform,
            "college": college,
            "mailer": mailer,
            "server": server,
            "limiter": limiter,
        },
    )
    server.shutdown()
    server.server_close()


def sign_up(api, email="asha@nmims.edu.in", password="secret123"):
    return requests.post(
        api.url + "/register",
        json={"name": "Asha", "email": email, "password": password, "college_id": api.college.college_id},
    )


def test_register_confirm_login_over_http(api):
    reg = sign_up(api)
    assert reg.status_code == 201 and reg.json()["verified"] is False
    assert (
        requests.post(api.url + "/login", json={"email": "asha@nmims.edu.in", "password": "secret123"}).status_code
        == 403
    )
    token = token_from(reg.json()["dev_link"])
    assert requests.post(api.url + "/email/verify", json={"token": token}).status_code == 200
    assert requests.post(api.url + "/email/verify", json={"token": token}).status_code == 400
    assert (
        requests.post(api.url + "/login", json={"email": "asha@nmims.edu.in", "password": "secret123"}).status_code
        == 200
    )


def test_verification_email_is_sent_with_a_link(api):
    sign_up(api)
    for _ in range(50):
        if api.mailer.sent:
            break
        threading.Event().wait(0.05)
    to, subject, body = api.mailer.sent[0]
    assert to == "asha@nmims.edu.in" and "Confirm" in subject and api.server.settings["base_url"] + "/?verify=" in body


def test_dev_links_never_appear_when_disabled(api):
    api.server.settings["dev_links"] = False
    assert "dev_link" not in sign_up(api).json()


def test_forgot_password_answers_identically_for_unknown_and_known(api):
    sign_up(api)
    known = requests.post(api.url + "/password/forgot", json={"email": "asha@nmims.edu.in"})
    unknown = requests.post(api.url + "/password/forgot", json={"email": "ghost@nmims.edu.in"})
    assert known.status_code == unknown.status_code == 202
    assert known.json()["status"] == unknown.json()["status"]
    assert "dev_link" in known.json() and "dev_link" not in unknown.json()  # dev convenience only, off in production


def test_full_reset_over_http_revokes_sessions(api):
    api.platform.require_email_verification = False
    sign_up(api)
    old = requests.post(api.url + "/login", json={"email": "asha@nmims.edu.in", "password": "secret123"}).json()[
        "token"
    ]
    link = requests.post(api.url + "/password/forgot", json={"email": "asha@nmims.edu.in"}).json()["dev_link"]
    assert (
        requests.post(
            api.url + "/password/reset", json={"token": token_from(link), "password": "a-new-secret-1"}
        ).status_code
        == 200
    )
    assert requests.get(api.url + "/me", headers={"Authorization": "Bearer " + old}).status_code == 401
    assert (
        requests.post(api.url + "/login", json={"email": "asha@nmims.edu.in", "password": "a-new-secret-1"}).status_code
        == 200
    )


def test_login_sets_httponly_samesite_cookie(api):
    api.platform.require_email_verification = False
    sign_up(api)
    res = requests.post(api.url + "/login", json={"email": "asha@nmims.edu.in", "password": "secret123"})
    cookie = res.headers["Set-Cookie"]
    assert "srp_session=" in cookie and "HttpOnly" in cookie and "SameSite=Strict" in cookie and "Path=/" in cookie
    assert "Secure" not in cookie  # plain http on loopback


def test_cookie_session_requires_csrf_header_on_writes(api):
    api.platform.require_email_verification = False
    sign_up(api)
    session = requests.Session()
    session.post(api.url + "/login", json={"email": "asha@nmims.edu.in", "password": "secret123"})
    assert session.get(api.url + "/me").status_code == 200
    blocked = session.put(api.url + "/me/preferences", json={"categories": ["sports"]})
    assert blocked.status_code == 403 and blocked.json()["error"] == "CrossSiteRequest"
    assert session.put(api.url + "/me/preferences", json={"categories": ["sports"]}, headers=CSRF).status_code == 200
    evil = session.put(
        api.url + "/me/preferences", json={"categories": ["sports"]}, headers={**CSRF, "Origin": "https://evil.example"}
    )
    assert evil.status_code == 403


def test_logout_clears_cookie_and_session(api):
    api.platform.require_email_verification = False
    sign_up(api)
    session = requests.Session()
    session.post(api.url + "/login", json={"email": "asha@nmims.edu.in", "password": "secret123"})
    out = session.post(api.url + "/logout", headers=CSRF)
    assert out.status_code == 200 and "Max-Age=0" in out.headers["Set-Cookie"]
    assert requests.get(api.url + "/me", headers={"Cookie": "srp_session=whatever"}).status_code == 401


def test_change_password_signs_out_other_devices_only(api):
    api.platform.require_email_verification = False
    sign_up(api)
    creds = {"email": "asha@nmims.edu.in", "password": "secret123"}
    here = requests.post(api.url + "/login", json=creds).json()["token"]
    other = requests.post(api.url + "/login", json=creds).json()["token"]
    res = requests.post(
        api.url + "/me/password",
        headers={"Authorization": "Bearer " + here},
        json={"current_password": "secret123", "new_password": "changed-secret-1"},
    )
    assert res.status_code == 200
    assert requests.get(api.url + "/me", headers={"Authorization": "Bearer " + here}).status_code == 200
    assert requests.get(api.url + "/me", headers={"Authorization": "Bearer " + other}).status_code == 401


def test_login_is_rate_limited_per_client(api):
    codes = [
        requests.post(api.url + "/login", json={"email": "x@nmims.edu.in", "password": "nope-nope"}).status_code
        for _ in range(22)
    ]
    assert codes.count(429) >= 1 and codes[0] == 401
    last = requests.post(api.url + "/login", json={"email": "x@nmims.edu.in", "password": "nope-nope"})
    assert last.status_code == 429 and int(last.headers["Retry-After"]) >= 1


def test_reset_requests_are_rate_limited_per_address(api):
    codes = [
        requests.post(api.url + "/password/forgot", json={"email": "asha@nmims.edu.in"}).status_code for _ in range(5)
    ]
    assert codes[:3] == [202, 202, 202] and codes[3] == 429


def test_security_headers_present(api):
    res = requests.get(api.url + "/")
    for header in (
        "Content-Security-Policy",
        "Referrer-Policy",
        "X-Frame-Options",
        "Permissions-Policy",
        "X-Content-Type-Options",
    ):
        assert header in res.headers
    assert "frame-ancestors 'none'" in res.headers["Content-Security-Policy"]
    assert res.headers["Referrer-Policy"] == "no-referrer"


def test_public_bind_requires_base_url():
    platform, _ = build_sample_platform(admin_password=ADMIN)
    with pytest.raises(RuntimeError):
        create_server(platform, "0.0.0.0", 0)


def test_dev_links_are_ignored_on_public_binds():
    platform, _ = build_sample_platform(admin_password=ADMIN)
    server = create_server(platform, "0.0.0.0", 0, base_url="https://platform.example.edu", dev_links=True)
    assert server.settings["dev_links"] is False and server.settings["base_url"] == "https://platform.example.edu"
    server.server_close()


def test_secure_cookie_and_hsts_behind_https_proxy(api, monkeypatch):
    from srp import config

    monkeypatch.setattr(config, "COOKIE_SECURE", "1")
    api.platform.require_email_verification = False
    sign_up(api)
    res = requests.post(api.url + "/login", json={"email": "asha@nmims.edu.in", "password": "secret123"})
    assert "Secure" in res.headers["Set-Cookie"] and "HttpOnly" in res.headers["Set-Cookie"]
    assert "max-age=31536000" in res.headers["Strict-Transport-Security"]
