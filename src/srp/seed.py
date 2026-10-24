from datetime import datetime, timedelta

from srp.service import Platform

CAMPUS = (19.1044, 72.8365)


def build_sample_platform(
    store=None,
    admin_password="admin-pass",  # noqa: S107
    admin_email="admin@platform.in",
    clock=datetime.now,
    require_email_verification=True,
):
    platform = Platform(clock=clock, store=store, require_email_verification=require_email_verification)
    mumbai = platform.add_city("Mumbai", "Maharashtra")
    college = platform.add_college("NMIMS MPSTME", "nmims.edu.in", mumbai.city_id, "Vile Parle, Mumbai")
    platform.add_recommendation(
        "Shree PG for Students", "pg_hostel", mumbai.city_id, 19.1044, 72.8365, 2, "Shared rooms with meals near campus"
    )
    platform.add_recommendation(
        "Campus Canteen", "restaurant", mumbai.city_id, 19.1050, 72.8370, 1, "Budget thali and snacks"
    )
    platform.add_recommendation(
        "Vile Parle Stationers",
        "stationery",
        mumbai.city_id,
        19.1030,
        72.8380,
        1,
        "Notebooks, drafting supplies, printouts",
    )
    platform.add_recommendation(
        "Juhu Sports Club", "sports", mumbai.city_id, 19.1075, 72.8263, 2, "Badminton and swimming"
    )
    platform.create_admin("Platform Admin", admin_email, admin_password)
    return platform, college


def load_demo_data(platform):
    city = next(iter(platform.cities.values()))
    today = platform.clock().date()
    listings = [
        (
            "Green Leaf Hostel",
            "pg_hostel",
            19.1062,
            72.8391,
            1,
            "Budget hostel, shared rooms",
            {"rent_range": "6000-8000", "gender_preference": "Any", "amenities": "WiFi, laundry"},
        ),
        (
            "Sunrise Girls PG",
            "pg_hostel",
            19.1011,
            72.8342,
            2,
            "Single and double rooms with meals",
            {"rent_range": "9000-12000", "gender_preference": "Female", "amenities": "WiFi, meals, AC"},
        ),
        (
            "Dosa Corner",
            "restaurant",
            19.1058,
            72.8352,
            1,
            "South Indian breakfast and lunch",
            {"cuisine_type": "South Indian", "price_range": "Under 150", "timings": "7am-10pm"},
        ),
        (
            "Pizza Point",
            "restaurant",
            19.1090,
            72.8400,
            2,
            "Student combo meals",
            {"cuisine_type": "Italian", "price_range": "200-400", "timings": "11am-11pm"},
        ),
        (
            "Print and Pen",
            "stationery",
            19.1049,
            72.8359,
            1,
            "Printing, binding and stationery",
            {"product_types": "Notebooks, printing", "timings": "9am-9pm"},
        ),
        (
            "Campus Courts",
            "sports",
            19.1021,
            72.8400,
            1,
            "Football and badminton courts",
            {"sport_types": "Football, badminton", "fee_structure": "100 per hour", "timings": "6am-9pm"},
        ),
    ]
    for name, category, lat, lon, price, description, details in listings:
        platform.add_recommendation(name, category, city.city_id, lat, lon, price, description, details=details)
    events = [
        ("Freshers Meetup", 3, "Cultural", "Student Council", "Main Auditorium"),
        ("Inter-College Football Cup", 9, "Sports", "Sports Committee", "Campus Courts"),
        ("Hackathon Weekend", 16, "Technical", "Coding Club", "Lab Block"),
    ]
    for name, offset, kind, organizer, venue in events:
        platform.add_recommendation(
            name,
            "event",
            city.city_id,
            19.1044,
            72.8365,
            0,
            f"{kind} event",
            venue,
            {"event_type": kind, "organizer": organizer, "venue": venue},
            today + timedelta(days=offset),
        )
