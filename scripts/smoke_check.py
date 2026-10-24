import os
import sys

import requests

BASE = os.environ.get("SRP_BASE_URL", "http://127.0.0.1:8000")
ADMIN_EMAIL = os.environ.get("SRP_ADMIN_EMAIL", "admin@platform.in")
ADMIN_PASSWORD = os.environ.get("SRP_ADMIN_PASSWORD", "")
STUDENT_EMAIL = os.environ.get("SRP_SMOKE_STUDENT", "smoke.student@nmims.edu.in")
STUDENT_PASSWORD = "smoke-test-pw-1"
failures = []


def check(label, response, expected):
    ok = response.status_code == expected
    print(f"[{'PASS' if ok else 'FAIL'}] {label}: HTTP {response.status_code} (expected {expected}) {response.text[:110]}")
    if not ok:
        failures.append(label)
    return response


def main():
    if not ADMIN_PASSWORD:
        sys.exit("Set SRP_ADMIN_PASSWORD to the administrator password of the running server.")
    check("GET /health", requests.get(BASE + "/health"), 200)
    college = requests.get(BASE + "/colleges").json()[0]["id"]
    body = {"name": "Smoke Student", "email": STUDENT_EMAIL, "password": STUDENT_PASSWORD, "college_id": college}
    check("POST /register (college email)", requests.post(BASE + "/register", json=body), 201)
    check("POST /register (non-college email)", requests.post(BASE + "/register", json={**body, "email": "x@gmail.com"}), 422)
    check("POST /register (look-alike domain)", requests.post(BASE + "/register", json={**body, "email": "x@notnmims.edu.in"}), 422)
    check("POST /register (same email, other case)", requests.post(BASE + "/register", json={**body, "email": STUDENT_EMAIL.upper()}), 409)
    login = check("POST /login", requests.post(BASE + "/login", json={"email": STUDENT_EMAIL, "password": STUDENT_PASSWORD}), 200)
    headers = {"Authorization": "Bearer " + login.json()["token"]}
    params = {"category": "pg_hostel", "lat": 19.1044, "lon": 72.8365}
    found = check("GET /search pg_hostel", requests.get(BASE + "/search", params=params), 200).json()["results"]
    check("GET /search (nothing within radius)", requests.get(BASE + "/search", params={**params, "lat": 28.6, "lon": 77.2}), 200)
    check("GET /events", requests.get(BASE + "/events"), 200)
    rec = found[0]["id"]
    review = check("POST /reviews", requests.post(BASE + "/reviews", json={"rec_id": rec, "rating": 5, "comment": "Smoke test review"}, headers=headers), 201)
    check("POST /reviews (rating 4.5)", requests.post(BASE + "/reviews", json={"rec_id": rec, "rating": 4.5, "comment": "x"}, headers=headers), 422)
    check("POST validate as student", requests.post(f"{BASE}/reviews/{review.json()['review_id']}/validate", json={"approve": True}, headers=headers), 403)
    admin = check("POST /login (admin)", requests.post(BASE + "/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}), 200)
    admin_headers = {"Authorization": "Bearer " + admin.json()["token"]}
    check("POST validate as admin", requests.post(f"{BASE}/reviews/{review.json()['review_id']}/validate", json={"approve": True}, headers=admin_headers), 200)
    after = requests.get(BASE + "/search", params=params).json()["results"]
    print("[INFO] rating shown in search after approval:", [r["rating"] for r in after if r["id"] == rec])
    for _ in range(5):
        requests.post(BASE + "/login", json={"email": STUDENT_EMAIL, "password": "wrong-password"})
    check("POST /login after 5 failures (locked)", requests.post(BASE + "/login", json={"email": STUDENT_EMAIL, "password": STUDENT_PASSWORD}), 423)
    check("GET /admin/audit", requests.get(BASE + "/admin/audit", headers=admin_headers), 200)
    check("POST /logout", requests.post(BASE + "/logout", headers=admin_headers), 200)
    check("GET /admin/audit after logout", requests.get(BASE + "/admin/audit", headers=admin_headers), 401)
    print("Smoke checks failed:" if failures else "All smoke checks passed.", failures or "")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
