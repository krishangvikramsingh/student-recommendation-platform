import json
import statistics
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from srp.seed import build_sample_platform, load_demo_data
from srp.security import hash_password
from srp.server import create_server
from srp.service import Platform
from srp.store import SqliteStore

USERS = 100_000
LISTINGS = 2_000
REVIEWS = 20_000
CONCURRENT = 500
PORT = 8766
BASE = f"http://127.0.0.1:{PORT}"


def bulk_load(db_path):
    store = SqliteStore(db_path)
    platform, college = build_sample_platform(store, "load-admin-pass")
    load_demo_data(platform)
    city = next(iter(platform.cities))
    db = store.db
    shared_hash = hash_password("load-test-pass")
    now = datetime.now().isoformat()
    db.executemany(
        "INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ((f"ST9{i:06d}", f"Load Student {i}", f"load{i}@nmims.edu.in", shared_hash, "student", college.college_id, "",
          1, 0, 0, None, "[]", "[]", now) for i in range(USERS)))
    categories = ["pg_hostel", "restaurant", "stationery", "sports"]
    db.executemany(
        "INSERT INTO recommendations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ((f"RC9{i:05d}", f"Load Listing {i}", categories[i % 4], city, 19.0 + (i % 100) * 0.002,
          72.8 + (i % 70) * 0.002, i % 4, 0.0, "load test listing", "", "{}", None, 1) for i in range(LISTINGS)))
    db.executemany(
        "INSERT INTO reviews VALUES (?,?,?,?,?,?,?,?,?)",
        ((f"RV9{i:06d}", f"ST9{i:06d}", f"RC9{i % LISTINGS:05d}", 1 + i % 5, "load test review", "Published", now, now,
          "AD0010") for i in range(REVIEWS)))
    db.execute("UPDATE recommendations SET average_rating = COALESCE((SELECT ROUND(AVG(rating), 1) FROM reviews "
               "WHERE reviews.rec_id = recommendations.rec_id AND status = 'Published'), 0)")
    db.commit()
    store.close()


def summarise(samples):
    ordered = sorted(samples)
    return {"count": len(ordered), "median_s": round(statistics.median(ordered), 4),
            "p95_s": round(ordered[int(len(ordered) * 0.95) - 1], 4), "max_s": round(ordered[-1], 4)}


def timed(fn):
    start = time.perf_counter()
    result = fn()
    return time.perf_counter() - start, result


def main():
    out = {"dataset": {"users": USERS + 1, "listings": LISTINGS + 10, "reviews": REVIEWS}}
    db_path = str(Path(tempfile.mkdtemp()) / "load.db")
    bulk_load(db_path)

    start = time.perf_counter()
    platform = Platform(store=SqliteStore(db_path))
    out["startup_load_s"] = round(time.perf_counter() - start, 2)
    server = create_server(platform, "127.0.0.1", PORT)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    search = lambda: requests.get(BASE + "/search", params={"category": "restaurant", "lat": 19.1, "lon": 72.85, "radius": 5})
    login = lambda n: requests.post(BASE + "/login", json={"email": f"load{n}@nmims.edu.in", "password": "load-test-pass"})

    sequential = {"search": [], "login": [], "listing": [], "health": []}
    for n in range(30):
        sequential["search"].append(timed(search)[0])
        sequential["login"].append(timed(lambda: login(n))[0])
        sequential["listing"].append(timed(lambda: requests.get(BASE + "/listings/RC900001"))[0])
        sequential["health"].append(timed(lambda: requests.get(BASE + "/health"))[0])
    out["sequential"] = {k: summarise(v) for k, v in sequential.items()}

    tokens = []
    with ThreadPoolExecutor(20) as pool:
        wall = time.perf_counter()
        logins = list(pool.map(lambda n: timed(lambda: login(n)), range(CONCURRENT)))
        out["login_ramp_wall_s"] = round(time.perf_counter() - wall, 2)
    out["login_ramp"] = summarise([t for t, _ in logins])
    out["login_ramp_ok"] = sum(r.status_code == 200 for _, r in logins)
    tokens = [r.json()["token"] for _, r in logins if r.status_code == 200]

    with ThreadPoolExecutor(CONCURRENT) as pool:
        wall = time.perf_counter()
        searches = list(pool.map(lambda _: timed(search), range(CONCURRENT)))
        out["concurrent_search_wall_s"] = round(time.perf_counter() - wall, 2)
    out["concurrent_search"] = summarise([t for t, _ in searches])
    out["concurrent_search_ok"] = sum(r.status_code == 200 for _, r in searches)

    def submit(index):
        headers = {"Authorization": "Bearer " + tokens[index]}
        rec = f"RC9{(index * 7 + 1) % LISTINGS:05d}"
        return timed(lambda: requests.post(BASE + "/reviews", json={"rec_id": rec, "rating": 4, "comment": f"load review {index}"},
                                          headers=headers))
    before = len(platform.reviews)
    with ThreadPoolExecutor(CONCURRENT) as pool:
        submissions = list(pool.map(submit, range(len(tokens))))
    created = sum(r.status_code == 201 for _, r in submissions)
    stored = len(platform.reviews) - before
    db_rows = SqliteStore(db_path).db.execute("SELECT COUNT(*) FROM reviews WHERE comment LIKE 'load review %'").fetchone()[0]
    out["review_submission"] = {"attempted": len(tokens), "http_201": created, "in_memory_new": stored,
                                "rows_in_database": db_rows, "latency": summarise([t for t, _ in submissions])}
    server.shutdown()
    server.server_close()

    start = time.perf_counter()
    reopened = Platform(store=SqliteStore(db_path))
    server = create_server(reopened, "127.0.0.1", PORT)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    healthy = requests.get(BASE + "/health").json()
    out["restart_recovery"] = {"seconds_to_healthy": round(time.perf_counter() - start, 2), "health": healthy,
                               "reviews_after_restart": len(reopened.reviews),
                               "users_after_restart": len(reopened.users)}
    server.shutdown()
    (ROOT / "docs" / "evidence" / "nfr_results.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
