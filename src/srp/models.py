from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum


class Category(str, Enum):
    PG_HOSTEL = "pg_hostel"
    RESTAURANT = "restaurant"
    STATIONERY = "stationery"
    SPORTS = "sports"
    EVENT = "event"


CATEGORY_FIELDS = {
    Category.PG_HOSTEL: ("rent_range", "gender_preference", "amenities"),
    Category.RESTAURANT: ("cuisine_type", "price_range", "timings"),
    Category.STATIONERY: ("product_types", "timings"),
    Category.SPORTS: ("sport_types", "fee_structure", "timings"),
    Category.EVENT: ("organizer", "venue", "event_type"),
}

NOTIFICATION_CATEGORIES = ("event", "review", "moderation", "account")


class ReviewStatus(str, Enum):
    PENDING = "Pending"
    UNDER_REVIEW = "Under Review"
    PUBLISHED = "Published"
    REJECTED = "Rejected"


@dataclass
class City:
    city_id: str
    name: str
    state: str


@dataclass
class College:
    college_id: str
    name: str
    domain: str
    city_id: str
    address: str = ""


@dataclass
class User:
    user_id: str
    name: str
    email: str
    password_hash: str
    role: str = "student"
    college_id: str = ""
    verified: bool = False
    suspended: bool = False
    failed_attempts: int = 0
    locked_until: datetime | None = None
    preferences: set = field(default_factory=set)
    disabled_notifications: set = field(default_factory=set)
    phone: str = ""
    created_at: datetime | None = None


@dataclass
class Recommendation:
    rec_id: str
    name: str
    category: Category
    city_id: str
    lat: float
    lon: float
    price_level: int = 0
    average_rating: float = 0.0
    description: str = ""
    address: str = ""
    details: dict = field(default_factory=dict)
    event_date: date | None = None
    active: bool = True


@dataclass
class Review:
    review_id: str
    user_id: str
    rec_id: str
    rating: int
    comment: str
    status: ReviewStatus = ReviewStatus.PENDING
    reports: dict = field(default_factory=dict)
    submitted_at: datetime = field(default_factory=datetime.now)
    validated_at: datetime | None = None
    validated_by: str = ""


@dataclass
class Notification:
    notification_id: int
    user_id: str
    category: str
    message: str
    created_at: datetime
    read: bool = False


@dataclass
class AuditEntry:
    entry_id: int
    at: datetime
    actor_id: str
    action: str
    target: str = ""
    detail: str = ""


@dataclass
class AuthToken:
    token_hash: str
    user_id: str
    purpose: str
    expires_at: datetime
    used_at: datetime | None = None
