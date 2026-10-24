from datetime import datetime, timedelta

import pytest

from srp.models import User
from srp.security import hash_password
from srp.seed import build_sample_platform


class FakeClock:
    def __init__(self):
        self.now = datetime(2026, 9, 18, 10, 0, 0)

    def __call__(self):
        return self.now

    def advance(self, **kwargs):
        self.now += timedelta(**kwargs)


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def world(clock):
    platform, college = build_sample_platform()
    platform.clock = clock
    platform.require_email_verification = False  # legacy suites predate email confirmation; see test_auth.py
    return platform, college


@pytest.fixture
def student(world):
    platform, college = world
    return platform.register("Asha Rao", "asha@nmims.edu.in", "secret123", college.college_id)


@pytest.fixture
def admin(world):
    platform, _ = world
    return platform.find_user("admin@platform.in")


@pytest.fixture
def unverified(world):
    platform, college = world
    user = User("ST9999", "Guest", "guest@gmail.com", hash_password("pw"), college_id=college.college_id)
    platform.users[user.user_id] = user
    return user
