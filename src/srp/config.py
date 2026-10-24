import os


def setting(name, default):
    return os.environ.get("SRP_" + name, default)


HOST = setting("HOST", "127.0.0.1")
PORT = int(setting("PORT", "8000"))
DB_PATH = setting("DB_PATH", "data/platform.db")
SESSION_MINUTES = int(setting("SESSION_MINUTES", "30"))
ADMIN_EMAIL = setting("ADMIN_EMAIL", "admin@platform.in")
ADMIN_PASSWORD = setting("ADMIN_PASSWORD", "")
LOAD_DEMO_DATA = setting("DEMO_DATA", "1") == "1"
SESSION_HOURS = int(setting("SESSION_HOURS", "12"))
BASE_URL = setting("BASE_URL", "")
COOKIE_SECURE = setting("COOKIE_SECURE", "auto")
TRUST_PROXY = setting("TRUST_PROXY", "0") == "1"
REQUIRE_EMAIL_VERIFICATION = setting("REQUIRE_EMAIL_VERIFICATION", "1") == "1"
MAIL = setting("MAIL", "console")
MAIL_FROM = setting("MAIL_FROM", "Student Platform <no-reply@localhost>")
SMTP_HOST = setting("SMTP_HOST", "")
SMTP_PORT = int(setting("SMTP_PORT", "587"))
SMTP_USER = setting("SMTP_USER", "")
SMTP_PASSWORD = setting("SMTP_PASSWORD", "")
DEV_LINKS = setting("DEV_LINKS", "0") == "1"
OUTBOX_PATH = setting("OUTBOX_PATH", "data/outbox.log")
