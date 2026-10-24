import json
import os
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from playwright.sync_api import sync_playwright

from srp.seed import build_sample_platform, load_demo_data
from srp.server import create_server
from srp.store import SqliteStore

OUT = ROOT / "docs" / "evidence" / "screens"
AXE = os.environ.get("SRP_AXE_PATH", "")
PORT = 8765
ADMIN_PASSWORD = "walkthrough-admin-1"
STUDENT_EMAIL = "demo.student@nmims.edu.in"
STUDENT_PASSWORD = "walkthrough-pw-1"


def start_server(db_path):
    store = SqliteStore(db_path)
    platform, _ = build_sample_platform(store, ADMIN_PASSWORD)
    load_demo_data(platform)
    server = create_server(platform, "127.0.0.1", PORT)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"clicks_register_and_search": None, "axe": {}, "mobile_overflow": None}
    db_path = Path(tempfile.mkdtemp()) / "walk.db"
    server = start_server(str(db_path))
    base = f"http://127.0.0.1:{PORT}"
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome") \
            if Path("/opt/pw-browsers/chromium-1194/chrome-linux/chrome").exists() else p.chromium.launch()
        page = browser.new_context(viewport={"width": 1180, "height": 820}, bypass_csp=True).new_page()
        clicks = {"n": 0}

        def click(target, name=None):
            clicks["n"] += 1
            page.get_by_role(target, name=name, exact=True).click()

        def search_button():
            return page.get_by_role("form", name="Search places").get_by_role("button", name="Search", exact=True)

        def nav_button(name):
            return page.get_by_role("navigation").get_by_role("button", name=name, exact=True)

        def shot(name):
            page.evaluate("window.scrollTo(0, 0)")
            page.mouse.move(2, 2)
            page.wait_for_timeout(900)
            page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)

        def scan(name):
            page.wait_for_timeout(900)
            if AXE and Path(AXE).exists():
                page.add_script_tag(path=AXE)
                result = page.evaluate("axe.run(document, {runOnly: ['wcag2a','wcag2aa','wcag21a','wcag21aa']})")
                report["axe"][name] = {"violations": [{"id": v["id"], "impact": v["impact"], "nodes": len(v["nodes"])}
                                                       for v in result["violations"]],
                                       "passes": len(result["passes"])}

        page.goto(base)
        scan("search")
        shot("01_home_search")
        click("button", "Log in / Register")
        scan("account")
        page.fill("#reg-name", "Demo Student")
        page.fill("#reg-email", STUDENT_EMAIL)
        page.fill("#reg-password", STUDENT_PASSWORD)
        shot("02_register")
        click("button", "Register")
        page.wait_for_selector("text=Account created")
        page.wait_for_selector("text=Search nearby places")
        clicks["n"] += 1
        search_button().click()
        page.wait_for_selector("#results article")
        report["clicks_register_and_search"] = clicks["n"]
        shot("03_search_results")
        scan("search_results")

        page.select_option("#category", "restaurant")
        page.select_option("#price", "1")
        search_button().click()
        page.wait_for_selector("#results article")
        shot("04_filtered_search")

        page.select_option("#category", "pg_hostel")
        page.select_option("#price", "")
        page.fill("#radius", "0.5")
        page.fill("#lat", "19.2000")
        page.fill("#lon", "72.9000")
        search_button().click()
        page.wait_for_selector("#results .msg")
        shot("05_empty_search")

        page.fill("#lat", "19.1044")
        page.fill("#lon", "72.8365")
        page.fill("#radius", "5")
        search_button().click()
        page.wait_for_selector("#results article")
        page.get_by_role("button", name="View details of Shree PG for Students").click()
        page.wait_for_selector("text=Write a review")
        page.select_option("#stars", "5")
        page.fill("#comment", "Clean rooms, good food and friendly staff.")
        page.get_by_role("button", name="Submit review").click()
        page.wait_for_selector("text=Review submitted")
        shot("06_review_submitted")
        scan("detail")

        nav_button("Log out").click()
        nav_button("Log in / Register").click()
        page.fill("#login-email", "admin@platform.in")
        page.fill("#login-password", ADMIN_PASSWORD)
        page.get_by_role("button", name="Log in", exact=True).click()
        page.wait_for_selector("text=Administrator dashboard")
        page.wait_for_selector("text=Reviews awaiting moderation")
        shot("07_admin_queue")
        scan("admin")
        page.get_by_role("button", name="Approve / keep").first.click()
        page.wait_for_selector("text=No reviews are waiting")
        shot("08_admin_after_approval")

        nav_button("Log out").click()
        nav_button("Search").click()
        page.select_option("#category", "pg_hostel")
        search_button().click()
        page.wait_for_selector("#results article")
        shot("09_rating_after_approval")

        nav_button("Events").click()
        page.wait_for_selector("#main article")
        shot("10_events")
        scan("events")

        nav_button("Log in / Register").click()
        page.fill("#login-email", STUDENT_EMAIL)
        page.fill("#login-password", STUDENT_PASSWORD)
        page.get_by_role("button", name="Log in", exact=True).click()
        nav_button("For you").click()
        page.wait_for_selector("text=Recommended for you")
        page.check("input[value=sports]")
        page.get_by_role("button", name="Save and show recommendations").click()
        page.wait_for_selector("text=Preferences saved")
        shot("11_recommendations")
        nav_button("Notifications").click()
        page.wait_for_selector("text=Turn off these notification types")
        shot("12_notifications")
        scan("notifications")

        mobile = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
        mobile.goto(base)
        mobile.get_by_role("form", name="Search places").get_by_role("button", name="Search", exact=True).click()
        mobile.wait_for_selector("#results article")
        report["mobile_overflow"] = mobile.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        mobile.screenshot(path=str(OUT / "13_mobile_search.png"), full_page=True)
        browser.close()
    server.shutdown()
    (ROOT / "docs" / "evidence" / "ui_walkthrough.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
