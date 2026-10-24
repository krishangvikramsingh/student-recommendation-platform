import json
import sqlite3
from datetime import date, datetime

from srp.models import (
    AuditEntry,
    AuthToken,
    Category,
    City,
    College,
    Notification,
    Recommendation,
    Review,
    ReviewStatus,
    User,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS cities (
    city_id TEXT PRIMARY KEY, name TEXT NOT NULL, state TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS colleges (
    college_id TEXT PRIMARY KEY, name TEXT NOT NULL, domain TEXT NOT NULL UNIQUE, address TEXT NOT NULL DEFAULT '',
    city_id TEXT NOT NULL REFERENCES cities(city_id));
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'admin')), college_id TEXT, phone TEXT NOT NULL DEFAULT '',
    verified INTEGER NOT NULL, suspended INTEGER NOT NULL, failed_attempts INTEGER NOT NULL, locked_until TEXT,
    preferences TEXT NOT NULL, disabled_notifications TEXT NOT NULL, created_at TEXT);
CREATE TABLE IF NOT EXISTS recommendations (
    rec_id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
    city_id TEXT NOT NULL REFERENCES cities(city_id), lat REAL NOT NULL, lon REAL NOT NULL,
    price_level INTEGER NOT NULL, average_rating REAL NOT NULL, description TEXT NOT NULL, address TEXT NOT NULL,
    details TEXT NOT NULL, event_date TEXT, active INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS idx_rec_category ON recommendations(category, active);
CREATE TABLE IF NOT EXISTS reviews (
    review_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id),
    rec_id TEXT NOT NULL REFERENCES recommendations(rec_id),
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5), comment TEXT NOT NULL, status TEXT NOT NULL,
    submitted_at TEXT NOT NULL, validated_at TEXT, validated_by TEXT NOT NULL DEFAULT '');
CREATE INDEX IF NOT EXISTS idx_review_rec ON reviews(rec_id, status);
CREATE TABLE IF NOT EXISTS review_reports (
    review_id TEXT NOT NULL REFERENCES reviews(review_id), user_id TEXT NOT NULL REFERENCES users(user_id),
    reason TEXT NOT NULL, PRIMARY KEY (review_id, user_id));
CREATE TABLE IF NOT EXISTS notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL REFERENCES users(user_id),
    category TEXT NOT NULL, message TEXT NOT NULL, created_at TEXT NOT NULL, read INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id);
CREATE TABLE IF NOT EXISTS auth_tokens (
    token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id), purpose TEXT NOT NULL,
    expires_at TEXT NOT NULL, used_at TEXT);
CREATE INDEX IF NOT EXISTS idx_token_user ON auth_tokens(user_id, purpose);
CREATE TABLE IF NOT EXISTS audit_log (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, actor_id TEXT NOT NULL, action TEXT NOT NULL,
    target TEXT NOT NULL DEFAULT '', detail TEXT NOT NULL DEFAULT '');
"""


def _dt(value):
    return datetime.fromisoformat(value) if value else None


def _iso(value):
    return value.isoformat() if value else None


class SqliteStore:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.execute("PRAGMA journal_mode = WAL")
        self.db.execute("PRAGMA synchronous = NORMAL")
        self.db.executescript(SCHEMA)
        self.db.commit()

    def close(self):
        self.db.close()

    def is_empty(self):
        return self.db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0

    def save_city(self, c):
        self.db.execute("INSERT OR REPLACE INTO cities VALUES (?,?,?)", (c.city_id, c.name, c.state))
        self.db.commit()

    def save_college(self, c):
        self.db.execute(
            "INSERT OR REPLACE INTO colleges VALUES (?,?,?,?,?)", (c.college_id, c.name, c.domain, c.address, c.city_id)
        )
        self.db.commit()

    def save_user(self, u, commit=True):
        self.db.execute(
            "INSERT OR REPLACE INTO users VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                u.user_id,
                u.name,
                u.email,
                u.password_hash,
                u.role,
                u.college_id or None,
                u.phone,
                int(u.verified),
                int(u.suspended),
                u.failed_attempts,
                _iso(u.locked_until),
                json.dumps(sorted(u.preferences)),
                json.dumps(sorted(u.disabled_notifications)),
                _iso(u.created_at),
            ),
        )
        if commit:
            self.db.commit()

    def save_recommendation(self, r):
        self.db.execute(
            "INSERT OR REPLACE INTO recommendations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                r.rec_id,
                r.name,
                r.category.value,
                r.city_id,
                r.lat,
                r.lon,
                r.price_level,
                r.average_rating,
                r.description,
                r.address,
                json.dumps(r.details),
                r.event_date.isoformat() if r.event_date else None,
                int(r.active),
            ),
        )
        self.db.commit()

    def save_review(self, r):
        self.db.execute(
            "INSERT OR REPLACE INTO reviews VALUES (?,?,?,?,?,?,?,?,?)",
            (
                r.review_id,
                r.user_id,
                r.rec_id,
                r.rating,
                r.comment,
                r.status.value,
                _iso(r.submitted_at),
                _iso(r.validated_at),
                r.validated_by,
            ),
        )
        for user_id, reason in r.reports.items():
            self.db.execute("INSERT OR IGNORE INTO review_reports VALUES (?,?,?)", (r.review_id, user_id, reason))
        self.db.commit()

    def add_notification(self, n):
        cur = self.db.execute(
            "INSERT INTO notifications (user_id, category, message, created_at, read) VALUES (?,?,?,?,?)",
            (n.user_id, n.category, n.message, _iso(n.created_at), int(n.read)),
        )
        self.db.commit()
        return cur.lastrowid

    def mark_notification(self, notification_id):
        self.db.execute("UPDATE notifications SET read = 1 WHERE notification_id = ?", (notification_id,))
        self.db.commit()

    def add_audit(self, e):
        cur = self.db.execute(
            "INSERT INTO audit_log (at, actor_id, action, target, detail) VALUES (?,?,?,?,?)",
            (_iso(e.at), e.actor_id, e.action, e.target, e.detail),
        )
        self.db.commit()
        return cur.lastrowid

    def save_auth_token(self, tok):
        self.db.execute(
            "INSERT OR REPLACE INTO auth_tokens VALUES (?,?,?,?,?)",
            (tok.token_hash, tok.user_id, tok.purpose, _iso(tok.expires_at), _iso(tok.used_at)),
        )
        self.db.commit()

    def delete_auth_tokens(self, hashes):
        self.db.executemany("DELETE FROM auth_tokens WHERE token_hash = ?", [(h,) for h in hashes])
        self.db.commit()

    def load(self):
        q = self.db.execute
        data: dict[str, list] = {
            "cities": [City(*row) for row in q("SELECT city_id, name, state FROM cities")],
            "colleges": [
                College(r[0], r[1], r[2], r[4], r[3])
                for r in q("SELECT college_id, name, domain, address, city_id FROM colleges")
            ],
            "users": [],
            "recommendations": [],
            "reviews": [],
            "notifications": [],
            "audit": [],
            "auth_tokens": [
                AuthToken(r[0], r[1], r[2], _dt(r[3]), _dt(r[4]))
                for r in q("SELECT token_hash, user_id, purpose, expires_at, used_at FROM auth_tokens")
            ],
        }
        for r in q(
            "SELECT user_id, name, email, password_hash, role, college_id, phone, verified, suspended, "
            "failed_attempts, locked_until, preferences, disabled_notifications, created_at FROM users"
        ):
            data["users"].append(
                User(
                    r[0],
                    r[1],
                    r[2],
                    r[3],
                    r[4],
                    r[5] or "",
                    bool(r[7]),
                    bool(r[8]),
                    r[9],
                    _dt(r[10]),
                    set(json.loads(r[11])),
                    set(json.loads(r[12])),
                    r[6],
                    _dt(r[13]),
                )
            )
        for r in q(
            "SELECT rec_id, name, category, city_id, lat, lon, price_level, average_rating, description, "
            "address, details, event_date, active FROM recommendations"
        ):
            data["recommendations"].append(
                Recommendation(
                    r[0],
                    r[1],
                    Category(r[2]),
                    r[3],
                    r[4],
                    r[5],
                    r[6],
                    r[7],
                    r[8],
                    r[9],
                    json.loads(r[10]),
                    date.fromisoformat(r[11]) if r[11] else None,
                    bool(r[12]),
                )
            )
        reports: dict = {}
        for review_id, user_id, reason in q("SELECT review_id, user_id, reason FROM review_reports"):
            reports.setdefault(review_id, {})[user_id] = reason
        for r in q(
            "SELECT review_id, user_id, rec_id, rating, comment, status, submitted_at, validated_at, "
            "validated_by FROM reviews"
        ):
            data["reviews"].append(
                Review(
                    r[0], r[1], r[2], r[3], r[4], ReviewStatus(r[5]), reports.get(r[0], {}), _dt(r[6]), _dt(r[7]), r[8]
                )
            )
        for r in q("SELECT notification_id, user_id, category, message, created_at, read FROM notifications"):
            data["notifications"].append(Notification(r[0], r[1], r[2], r[3], _dt(r[4]), bool(r[5])))
        for r in q("SELECT entry_id, at, actor_id, action, target, detail FROM audit_log"):
            data["audit"].append(AuditEntry(r[0], _dt(r[1]), r[2], r[3], r[4], r[5]))
        return data
