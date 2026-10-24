import smtplib
import sys
import threading
from email.message import EmailMessage
from pathlib import Path

from srp import config


class ConsoleMailer:
    """Development mailer: prints each message and appends it to an outbox file."""

    def __init__(self, outbox=None):
        self.outbox = Path(outbox) if outbox else None
        self.sent = []

    def send(self, to, subject, body):
        self.sent.append((to, subject, body))
        text = f"--- mail to {to} ---\nSubject: {subject}\n\n{body}\n"
        print(text, file=sys.stderr)
        if self.outbox:
            self.outbox.parent.mkdir(parents=True, exist_ok=True)
            with self.outbox.open("a") as handle:
                handle.write(text)


class SmtpMailer:
    def __init__(self, host, port, user, password, sender):
        self.host, self.port, self.user, self.password, self.sender = host, port, user, password, sender

    def send(self, to, subject, body):
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = self.sender, to, subject
        message.set_content(body)
        with smtplib.SMTP(self.host, self.port, timeout=15) as smtp:
            smtp.starttls()
            if self.user:
                smtp.login(self.user, self.password)
            smtp.send_message(message)


def from_config():
    if config.MAIL == "smtp":
        if not config.SMTP_HOST:
            raise SystemExit("SRP_MAIL=smtp needs SRP_SMTP_HOST (and usually SRP_SMTP_USER / SRP_SMTP_PASSWORD).")
        return SmtpMailer(config.SMTP_HOST, config.SMTP_PORT, config.SMTP_USER, config.SMTP_PASSWORD, config.MAIL_FROM)
    return ConsoleMailer(config.OUTBOX_PATH)


def send_in_background(mailer, to, subject, body):
    """Send off the request thread so response time never reveals whether an account exists."""

    def run():
        try:
            mailer.send(to, subject, body)
        except Exception as exc:
            print("mail delivery failed:", type(exc).__name__, file=sys.stderr)

    threading.Thread(target=run, daemon=True).start()
