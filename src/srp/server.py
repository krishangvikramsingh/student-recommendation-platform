import hashlib
import ipaddress
import json
import mimetypes
import re
import secrets
import sys
from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from srp import config
from srp.errors import (
    AccountLocked,
    AccountSuspended,
    DuplicateAccount,
    DuplicateReport,
    DuplicateReview,
    EmailNotVerified,
    InvalidCollegeEmail,
    InvalidCredentials,
    InvalidInput,
    InvalidReview,
    InvalidToken,
    NotAuthorised,
    NotFound,
    NotVerified,
    PlatformError,
    RateLimited,
)
from srp.mailer import ConsoleMailer, send_in_background
from srp.models import Category
from srp.ratelimit import RateLimiter

WEB_ROOT = Path(__file__).parent / "web"
MAX_BODY = 64 * 1024

STATUS = {
    DuplicateAccount: 409,
    DuplicateReview: 409,
    InvalidCollegeEmail: 422,
    InvalidCredentials: 401,
    AccountLocked: 423,
    AccountSuspended: 403,
    NotVerified: 403,
    NotAuthorised: 403,
    InvalidReview: 422,
    InvalidInput: 422,
    DuplicateReport: 409,
    NotFound: 404,
    EmailNotVerified: 403,
    InvalidToken: 400,
    RateLimited: 429,
}
COOKIE = "srp_session"
CSRF_HEADER = "X-Requested-With"
CSRF_VALUE = "srp"


class Sessions:
    """In-memory sessions. Only a SHA-256 of each token is kept, so a memory dump cannot be replayed."""

    def __init__(self, minutes, clock=datetime.now, max_hours=config.SESSION_HOURS):
        self.idle = timedelta(minutes=minutes)
        self.absolute = timedelta(hours=max_hours)
        self.clock = clock
        self.items = {}

    @staticmethod
    def _key(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def open(self, user_id):
        token = secrets.token_urlsafe(32)
        now = self.clock()
        self.items[self._key(token)] = [user_id, now, now]
        return token

    def user_for(self, token):
        if not token:
            return None
        key = self._key(token)
        entry = self.items.get(key)
        if entry is None:
            return None
        now = self.clock()
        if now - entry[1] > self.idle or now - entry[2] > self.absolute:
            del self.items[key]
            return None
        entry[1] = now
        return entry[0]

    def close(self, token):
        self.items.pop(self._key(token), None)

    def revoke_user(self, user_id, keep=None):
        spare = self._key(keep) if keep else None
        for key in [k for k, (uid, _, _) in self.items.items() if uid == user_id and k != spare]:
            del self.items[key]


def mask_email(email):
    local, _, domain = email.partition("@")
    return local[:1] + "***@" + domain


def rec_json(rec, distance=None, review_count=None):
    body = {
        "id": rec.rec_id,
        "name": rec.name,
        "category": rec.category.value,
        "rating": rec.average_rating,
        "price_level": rec.price_level,
        "description": rec.description,
        "address": rec.address,
        "lat": rec.lat,
        "lon": rec.lon,
        "details": rec.details,
        "event_date": rec.event_date.isoformat() if rec.event_date else None,
    }
    if distance is not None:
        body["distance_km"] = distance
    if review_count is not None:
        body["review_count"] = review_count
    return body


def session_cookie(token, max_age, secure):
    parts = [f"{COOKIE}={token}", "HttpOnly", "SameSite=Strict", "Path=/", f"Max-Age={max_age}"]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def build_app(platform, sessions, mailer, limiter, settings):
    def public_review(review):
        author = platform.users[review.user_id].name
        return {
            "id": review.review_id,
            "author": author,
            "rating": review.rating,
            "comment": review.comment,
            "submitted_at": review.submitted_at.isoformat(),
        }

    def moderation_json(review):
        return {
            "id": review.review_id,
            "listing": platform.recommendations[review.rec_id].name,
            "author": platform.users[review.user_id].name,
            "rating": review.rating,
            "comment": review.comment,
            "status": review.status.value,
            "reports": list(review.reports.values()),
        }

    def student_json(user):
        return {
            "id": user.user_id,
            "name": user.name,
            "email": mask_email(user.email),
            "verified": user.verified,
            "suspended": user.suspended,
            "college_id": user.college_id,
        }

    def note_json(n):
        return {
            "id": n.notification_id,
            "category": n.category,
            "message": n.message,
            "read": n.read,
            "created_at": n.created_at.isoformat(),
        }

    def need(body, *keys):
        missing = [k for k in keys if k not in body]
        if missing:
            raise InvalidInput(",".join(missing))
        return [body[k] for k in keys]

    def coords(query):
        try:
            return float(query["lat"]), float(query["lon"])
        except (KeyError, ValueError):
            raise InvalidInput("lat,lon") from None

    def optional_float(query, name):
        return float(query[name]) if name in query else None

    routes = []

    def route(method, pattern, auth="public"):
        def decorate(fn):
            routes.append((method, re.compile("^" + pattern + "$"), auth, fn))
            return fn

        return decorate

    @route("GET", "/health")
    def health(ctx):
        return 200, {"status": "ok"}

    @route("GET", "/colleges")
    def colleges(ctx):
        return 200, [{"id": c.college_id, "name": c.name, "city_id": c.city_id} for c in platform.colleges.values()]

    @route("GET", "/cities")
    def cities(ctx):
        return 200, [{"id": c.city_id, "name": c.name, "state": c.state} for c in platform.cities.values()]

    def limit(ctx, name, count, window, key=None):
        limiter.check(f"{name}:{key or ctx.ip}", count, window)

    def send_link(user, purpose, raw):
        path = {"verify": "/?verify=", "reset": "/?reset="}[purpose]
        link = settings["base_url"] + path + raw
        if purpose == "verify":
            subject = "Confirm your email for the Student Recommendation Platform"
            body = (
                f"Hi {user.name},\n\nConfirm your college email to activate your account:\n{link}\n\n"
                "The link works once and expires in 24 hours. If you did not sign up, ignore this message."
            )
        else:
            subject = "Reset your Student Recommendation Platform password"
            body = (
                f"Hi {user.name},\n\nChoose a new password here:\n{link}\n\n"
                "The link works once and expires in 1 hour. If you did not ask for this, ignore this message "
                "and your password stays as it is."
            )
        send_in_background(mailer, user.email, subject, body)
        return link

    def generic(link, message):
        body = {"status": message}
        if settings["dev_links"] and link:
            body["dev_link"] = link
        return 202, body

    @route("POST", "/register")
    def register(ctx):
        limit(ctx, "register", 10, 600)
        name, email, password, college_id = need(ctx.body, "name", "email", "password", "college_id")
        user = platform.register(name, email, password, college_id, ctx.body.get("phone", ""))
        body = {"user_id": user.user_id, "verified": user.verified}
        if not user.verified:
            issued = platform.verification_token(user.email)
            link = send_link(issued[0], "verify", issued[1])
            body["verification_sent"] = True
            if settings["dev_links"]:
                body["dev_link"] = link
        return 201, body

    @route("POST", "/login")
    def login(ctx):
        email, password = need(ctx.body, "email", "password")
        limit(ctx, "login", 20, 60)
        user = platform.login(email, password)
        token = sessions.open(user.user_id)
        ctx.out.append(("Set-Cookie", session_cookie(token, int(sessions.absolute.total_seconds()), ctx.secure)))
        return 200, {"token": token, "role": user.role, "name": user.name}

    @route("POST", "/email/verify")
    def email_verify(ctx):
        limit(ctx, "token", 20, 900)
        (token,) = need(ctx.body, "token")
        user = platform.confirm_email(token)
        return 200, {"verified": True, "email": mask_email(user.email)}

    @route("POST", "/email/resend")
    def email_resend(ctx):
        limit(ctx, "mail", 5, 900)
        (email,) = need(ctx.body, "email")
        limit(ctx, "mail-to", 3, 3600, str(email).strip().lower())
        issued = platform.verification_token(email)
        link = send_link(issued[0], "verify", issued[1]) if issued else None
        return generic(link, "If that address has an account waiting for confirmation, a new link is on its way.")

    @route("POST", "/password/forgot")
    def password_forgot(ctx):
        limit(ctx, "mail", 5, 900)
        (email,) = need(ctx.body, "email")
        limit(ctx, "mail-to", 3, 3600, str(email).strip().lower())
        issued = platform.reset_token(email)
        link = send_link(issued[0], "reset", issued[1]) if issued else None
        return generic(link, "If that address has an account, a reset link is on its way.")

    @route("POST", "/password/reset")
    def password_reset(ctx):
        limit(ctx, "token", 20, 900)
        token, password = need(ctx.body, "token", "password")
        user = platform.reset_password(token, password)
        sessions.revoke_user(user.user_id)
        return 200, {"status": "Password updated. You can log in now."}

    @route("POST", "/me/password", "user")
    def change_password(ctx):
        limit(ctx, "pwchange", 5, 900, ctx.user_id)
        current, new = need(ctx.body, "current_password", "new_password")
        platform.change_password(ctx.user_id, current, new)
        sessions.revoke_user(ctx.user_id, keep=ctx.token)
        return 200, {"status": "Password updated. Other devices were signed out."}

    @route("GET", "/search")
    def search(ctx):
        lat, lon = coords(ctx.query)
        outcome = platform.search(
            ctx.query.get("category", ""),
            lat,
            lon,
            float(ctx.query.get("radius", 5)),
            optional_float(ctx.query, "max_price"),
            optional_float(ctx.query, "min_rating"),
            min(int(ctx.query.get("limit", 50)), 200),
        )
        results = [rec_json(i["rec"], i["distance_km"], i["review_count"]) for i in outcome["results"]]
        return 200, {"results": results, "message": outcome["message"]}

    @route("GET", "/events")
    def events(ctx):
        found = platform.list_events(
            ctx.query.get("city_id"), ctx.query.get("event_type"), ctx.query.get("date_from"), ctx.query.get("date_to")
        )
        return 200, {
            "results": [rec_json(r) for r in found],
            "message": "" if found else "No upcoming events match these filters.",
        }

    @route("GET", "/listings/([A-Z0-9]+)")
    def listing(ctx, rec_id):
        rec = platform.get_recommendation(rec_id)
        reviews = platform.published_reviews(rec_id)
        body = rec_json(rec, review_count=len(reviews))
        body["reviews"] = [public_review(r) for r in reviews]
        return 200, body

    @route("POST", "/logout", "user")
    def logout(ctx):
        sessions.close(ctx.token)
        ctx.out.append(("Set-Cookie", session_cookie("", 0, ctx.secure)))
        return 200, {"status": "logged out"}

    @route("GET", "/me", "user")
    def me(ctx):
        u = platform.users[ctx.user_id]
        return 200, {
            "id": u.user_id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "verified": u.verified,
            "preferences": sorted(u.preferences),
            "disabled_notifications": sorted(u.disabled_notifications),
            "categories": [c.value for c in Category],
        }

    @route("PUT", "/me/preferences", "user")
    def preferences(ctx):
        (categories,) = need(ctx.body, "categories")
        return 200, {"preferences": sorted(platform.set_preferences(ctx.user_id, categories).preferences)}

    @route("GET", "/recommend", "user")
    def recommend(ctx):
        lat, lon = coords(ctx.query)
        recs = platform.recommend(ctx.user_id, lat, lon, float(ctx.query.get("radius", 5)))
        return 200, {"results": [rec_json(r) for r in recs]}

    @route("GET", "/notifications", "user")
    def notifications(ctx):
        return 200, [note_json(n) for n in platform.notifications(ctx.user_id)]

    @route("POST", "/notifications/(\\d+)/read", "user")
    def read_notification(ctx, note_id):
        return 200, note_json(platform.mark_notification_read(ctx.user_id, int(note_id)))

    @route("PUT", "/me/notification-settings", "user")
    def notification_settings(ctx):
        (disabled,) = need(ctx.body, "disabled")
        return 200, {
            "disabled": sorted(platform.set_notification_settings(ctx.user_id, disabled).disabled_notifications)
        }

    @route("POST", "/reviews", "user")
    def submit_review(ctx):
        rec_id, rating, comment = need(ctx.body, "rec_id", "rating", "comment")
        review = platform.submit_review(ctx.user_id, rec_id, rating, comment)
        return 201, {"review_id": review.review_id, "status": review.status.value}

    @route("POST", "/reviews/([A-Z0-9]+)/report", "user")
    def report_review(ctx, review_id):
        (reason,) = need(ctx.body, "reason")
        review = platform.report_review(ctx.user_id, review_id, reason)
        return 200, {"review_id": review.review_id, "status": review.status.value}

    @route("POST", "/reviews/([A-Z0-9]+)/validate", "user")
    def validate_review(ctx, review_id):
        review = platform.validate_review(ctx.user_id, review_id, bool(ctx.body.get("approve")))
        return 200, {"review_id": review.review_id, "status": review.status.value}

    @route("GET", "/admin/reviews", "user")
    def admin_reviews(ctx):
        return 200, [moderation_json(r) for r in platform.moderation_queue(ctx.user_id)]

    @route("GET", "/admin/users", "user")
    def admin_users(ctx):
        return 200, [student_json(u) for u in platform.list_students(ctx.user_id)]

    @route("POST", "/admin/users/([A-Z0-9]+)/(verify|suspend|reinstate)", "user")
    def admin_user_action(ctx, user_id, action):
        if action == "verify":
            platform.verify_student(ctx.user_id, user_id)
        elif action == "suspend":
            platform.suspend_user(ctx.user_id, user_id)
            sessions.revoke_user(user_id)
        else:
            platform.reinstate_user(ctx.user_id, user_id)
        return 200, student_json(platform.users[user_id])

    @route("POST", "/admin/cities", "user")
    def admin_city(ctx):
        name, state = need(ctx.body, "name", "state")
        return 201, {"id": platform.create_city(ctx.user_id, name, state).city_id}

    @route("POST", "/admin/colleges", "user")
    def admin_college(ctx):
        name, domain, city_id = need(ctx.body, "name", "domain", "city_id")
        return 201, {
            "id": platform.create_college(ctx.user_id, name, domain, city_id, ctx.body.get("address", "")).college_id
        }

    @route("POST", "/admin/listings", "user")
    def admin_listing(ctx):
        b = ctx.body
        name, category, city_id, lat, lon = need(b, "name", "category", "city_id", "lat", "lon")
        rec = platform.create_recommendation(
            ctx.user_id,
            name,
            category,
            city_id,
            lat,
            lon,
            b.get("price_level", 0),
            b.get("description", ""),
            b.get("address", ""),
            b.get("details"),
            b.get("event_date"),
        )
        return 201, rec_json(rec)

    @route("PUT", "/admin/listings/([A-Z0-9]+)", "user")
    def admin_listing_update(ctx, rec_id):
        return 200, rec_json(platform.update_recommendation(ctx.user_id, rec_id, **ctx.body))

    @route("DELETE", "/admin/listings/([A-Z0-9]+)", "user")
    def admin_listing_delete(ctx, rec_id):
        platform.delete_recommendation(ctx.user_id, rec_id)
        return 200, {"status": "archived"}

    @route("GET", "/admin/audit", "user")
    def admin_audit(ctx):
        return 200, [
            {
                "id": e.entry_id,
                "at": e.at.isoformat(),
                "actor": e.actor_id,
                "action": e.action,
                "target": e.target,
                "detail": e.detail,
            }
            for e in platform.audit_entries(ctx.user_id)
        ]

    return routes


class Context:
    def __init__(self, query, body, token, user_id, ip="", secure=False):
        self.query, self.body, self.token, self.user_id = query, body, token, user_id
        self.ip, self.secure, self.out = ip, secure, []


def make_handler(platform, sessions, mailer, limiter, settings):
    routes = build_app(platform, sessions, mailer, limiter, settings)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def client_ip(self):
            if config.TRUST_PROXY:
                forwarded = self.headers.get("X-Forwarded-For", "").split(",")[-1].strip()
                if forwarded:
                    return forwarded
            return self.client_address[0]

        def is_secure(self):
            mode = config.COOKIE_SECURE
            if mode in ("1", "0"):
                return mode == "1"
            return config.TRUST_PROXY and self.headers.get("X-Forwarded-Proto", "") == "https"

        def send(self, code, data, content_type="application/json", extra=()):
            self.send_response(code)
            for name, value in extra:
                self.send_header(name, value)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self'; script-src 'self'; "
                "img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            )
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Cross-Origin-Opener-Policy", "same-origin")
            self.send_header("Permissions-Policy", "geolocation=(self), camera=(), microphone=()")
            if self.is_secure():
                self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
            self.end_headers()
            self.wfile.write(data)

        def reply(self, code, body, extra=()):
            self.send(code, json.dumps(body).encode(), extra=extra)

        def serve_static(self, path):
            name = "index.html" if path in ("/", "") else path.lstrip("/")
            target = (WEB_ROOT / name).resolve()
            if WEB_ROOT.resolve() not in target.parents or not target.is_file():
                return self.reply(404, {"error": "NotFound", "message": "Unknown route."})
            kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            self.send(200, target.read_bytes(), kind)

        def read_body(self):
            size = int(self.headers.get("Content-Length") or 0)
            if size > MAX_BODY:
                raise InvalidInput("body too large")
            raw = self.rfile.read(size) if size else b"{}"
            body = json.loads(raw or b"{}")
            if not isinstance(body, dict):
                raise InvalidInput("body")
            return body

        def same_origin_request(self):
            if self.headers.get(CSRF_HEADER) != CSRF_VALUE:
                return False
            origin = self.headers.get("Origin")
            return not origin or urlparse(origin).netloc == self.headers.get("Host", "")

        def dispatch(self, method):
            url = urlparse(self.path)
            query = {k: v[0] for k, v in parse_qs(url.query).items()}
            if method == "GET" and not any(m == "GET" and p.match(url.path) for m, p, _, _ in routes):
                return self.serve_static(url.path)
            try:
                token = self.headers.get("Authorization", "").removeprefix("Bearer ")
                if not token:
                    cookie = SimpleCookie(self.headers.get("Cookie", "")).get(COOKIE)
                    token = cookie.value if cookie else ""
                    if token and method not in ("GET", "HEAD") and not self.same_origin_request():
                        return self.reply(
                            403, {"error": "CrossSiteRequest", "message": "This request was blocked for your safety."}
                        )
                user_id = sessions.user_for(token)
                for route_method, pattern, auth, handler in routes:
                    match = pattern.match(url.path)
                    if route_method != method or not match:
                        continue
                    if auth == "user" and user_id is None:
                        return self.reply(401, {"error": "LoginRequired", "message": "Please log in first."})
                    body = self.read_body() if method in ("POST", "PUT") else {}
                    ctx = Context(query, body, token, user_id, self.client_ip(), self.is_secure())
                    code, payload = handler(ctx, *match.groups())
                    return self.reply(code, payload, ctx.out)
                return self.reply(404, {"error": "NotFound", "message": "Unknown route."})
            except PlatformError as exc:
                extra = [("Retry-After", str(exc.retry_after))] if isinstance(exc, RateLimited) else []
                return self.reply(
                    STATUS.get(type(exc), 400), {"error": type(exc).__name__, "message": exc.message}, extra
                )
            except (KeyError, ValueError, TypeError, json.JSONDecodeError):
                return self.reply(400, {"error": "BadRequest", "message": "Malformed request."})
            except Exception:
                print("unhandled error while serving", method, url.path, file=sys.stderr)
                return self.reply(500, {"error": "ServerError", "message": "Something went wrong."})

        def do_GET(self):
            self.dispatch("GET")

        def do_POST(self):
            self.dispatch("POST")

        def do_PUT(self):
            self.dispatch("PUT")

        def do_DELETE(self):
            self.dispatch("DELETE")

    return Handler


class PlatformServer(ThreadingHTTPServer):
    request_queue_size = 1024
    sessions: object
    settings: object
    daemon_threads = True


def is_loopback(host):
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host == "localhost"


def create_server(
    platform,
    host=config.HOST,
    port=config.PORT,
    session_minutes=config.SESSION_MINUTES,
    mailer=None,
    limiter=None,
    base_url=None,
    dev_links=None,
):
    """base_url is used in emailed links; it is never taken from request headers (host-header poisoning)."""
    base_url = base_url or config.BASE_URL
    if not base_url and not is_loopback(host):
        raise RuntimeError("Set SRP_BASE_URL (for example https://platform.example.edu) when binding a public address.")
    sessions = Sessions(session_minutes)
    settings = {
        "base_url": base_url.rstrip("/") if base_url else "",
        "dev_links": (config.DEV_LINKS if dev_links is None else dev_links) and is_loopback(host),
    }
    httpd = PlatformServer(
        (host, port), make_handler(platform, sessions, mailer or ConsoleMailer(), limiter or RateLimiter(), settings)
    )
    if not settings["base_url"]:
        settings["base_url"] = f"http://{host}:{httpd.server_address[1]}"
    httpd.sessions = sessions
    httpd.settings = settings
    return httpd
