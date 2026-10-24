import base64
import hashlib
import hmac
import os
import secrets

N, R, P = 2**14, 8, 1


def hash_password(password):
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=N, r=R, p=P, dklen=32)
    return f"scrypt${N}${R}${P}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password, stored):
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        candidate = hashlib.scrypt(
            password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=32
        )
        return hmac.compare_digest(candidate, base64.b64decode(digest))
    except (ValueError, TypeError):
        return False


DUMMY_HASH = hash_password("not-a-real-password")


def new_token():
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def hash_token(raw):
    return hashlib.sha256(raw.encode()).hexdigest()
