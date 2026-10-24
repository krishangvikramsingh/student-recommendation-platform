import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyBboxPatch, Rectangle

plt.rcParams["font.family"] = "Liberation Sans"
NAVY, BLUE, PALE, LINE = "#1e3a8a", "#1d4ed8", "#e0e7ff", "#475569"


def box(ax, x, y, w, h, title, lines=(), fill=PALE, edge=BLUE, tcolor=NAVY):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=fill, ec=edge, lw=1.6))
    ax.text(x + w / 2, y + h - 0.28, title, ha="center", va="top", fontsize=10.5, fontweight="bold", color=tcolor)
    for i, line in enumerate(lines):
        ax.text(x + w / 2, y + h - 0.68 - i * 0.3, line, ha="center", va="top", fontsize=8.3, color="#1b2430")


def arrow(ax, p, q, label="", both=False, dy=0.12, ha="center"):
    ax.annotate("", xy=q, xytext=p, arrowprops=dict(arrowstyle="<|-|>" if both else "-|>", color=LINE, lw=1.5))
    if label:
        ax.text((p[0] + q[0]) / 2, (p[1] + q[1]) / 2 + dy, label, ha=ha, fontsize=8, color=LINE)


def architecture(path):
    fig, ax = plt.subplots(figsize=(10, 6.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6.2)
    ax.axis("off")
    box(ax, 0.3, 4.7, 9.4, 1.35, "Presentation layer  (src/srp/web)", ["Single-page web UI: index.html, app.js, style.css",
        "Search, Events, For you, Notifications, Account, Administrator dashboard (responsive, keyboard accessible)"])
    box(ax, 0.3, 2.95, 9.4, 1.35, "Interface layer  (srp/server.py)", ["HTTP/JSON router, bearer-token sessions with idle timeout, role check per route",
        "Safe error mapping (no stack traces), security headers, request size limit, static file serving"])
    box(ax, 0.3, 1.0, 5.6, 1.6, "Application / domain layer  (srp/service.py)", ["Platform: registration, login lockout, search, recommend,",
        "reviews, moderation, notifications, admin management, audit log",
        "Models: srp/models.py   Errors: srp/errors.py   Hashing: srp/security.py"])
    box(ax, 6.3, 1.0, 3.4, 1.6, "Persistence  (srp/store.py)", ["SQLite file data/platform.db", "write-through, constraints,", "foreign keys, indexes"], fill="#dbeafe")
    arrow(ax, (5, 4.7), (5, 4.3), "", both=True)
    ax.text(5.15, 4.5, "HTTP + JSON (REST)", fontsize=8, color=LINE, va="center")
    arrow(ax, (3, 2.95), (3, 2.6), "", both=True)
    ax.text(3.15, 2.78, "method calls", fontsize=8, color=LINE, va="center")
    arrow(ax, (5.9, 1.8), (6.3, 1.8), "", both=True)
    ax.text(5.0, 0.55, "Supporting: pytest suite (tests/), smoke_check.py, nfr_checks.py, ui_walkthrough.py (scripts/)", ha="center", fontsize=8.5, color=LINE)
    ax.text(5.0, 0.2, "Deployment: one Python process, python -m srp, http://127.0.0.1:8000 (configuration via SRP_* environment variables)", ha="center", fontsize=8.5, color=LINE)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")


def stick(ax, x, y, name):
    ax.add_patch(plt.Circle((x, y + 0.9), 0.17, fc="white", ec=NAVY, lw=1.6))
    ax.plot([x, x], [y + 0.73, y + 0.25], color=NAVY, lw=1.6)
    ax.plot([x - 0.3, x + 0.3], [y + 0.58, y + 0.58], color=NAVY, lw=1.6)
    ax.plot([x, x - 0.25], [y + 0.25, y - 0.1], color=NAVY, lw=1.6)
    ax.plot([x, x + 0.25], [y + 0.25, y - 0.1], color=NAVY, lw=1.6)
    ax.text(x, y - 0.35, name, ha="center", fontsize=10, fontweight="bold", color=NAVY)


def usecase(path):
    fig, ax = plt.subplots(figsize=(10, 7.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7.4)
    ax.axis("off")
    ax.add_patch(Rectangle((1.5, 0.2), 7.0, 7.0, fc="white", ec=NAVY, lw=1.6))
    ax.text(5, 7.0, "Student Recommendation Platform", ha="center", va="top", fontsize=11, fontweight="bold", color=NAVY)
    student = [("Register Account", 6.3), ("Verify College Email", 5.7), ("Login", 5.1), ("Search Recommendations", 4.5),
               ("View Details / Events", 3.9), ("Submit Review", 3.3), ("Report Review", 2.7), ("Personalised Recommendations", 2.1),
               ("Manage Notifications", 1.5)]
    admin = [("Validate / Moderate Review", 6.0), ("Manage Students", 5.2), ("Manage Colleges and Cities", 4.4),
             ("Manage Recommendations", 3.6), ("View Audit Log", 2.8)]
    pos = {}
    for name, y in student:
        ax.add_patch(Ellipse((3.0, y), 2.5, 0.52, fc="#e0e7ff", ec=BLUE, lw=1.3))
        ax.text(3.0, y, name, ha="center", va="center", fontsize=8.2)
        pos[name] = (3.0, y)
    for name, y in admin:
        ax.add_patch(Ellipse((7.1, y), 2.6, 0.52, fc="#e0e7ff", ec=BLUE, lw=1.3))
        ax.text(7.1, y, name, ha="center", va="center", fontsize=8.2)
        pos[name] = (7.1, y)
    stick(ax, 0.7, 3.6, "Student")
    stick(ax, 9.3, 3.6, "Administrator")
    for name, y in student:
        ax.plot([0.95, pos[name][0] - 1.25], [4.2, y], color="#64748b", lw=0.8)
    for name, y in admin:
        ax.plot([9.05, pos[name][0] + 1.3], [4.2, y], color="#64748b", lw=0.8)

    def include(a, b, label="<<include>>"):
        ya, yb = pos[a][1], pos[b][1]
        rad = -0.55 if yb < ya else 0.55
        ax.annotate("", xy=(4.2, yb), xytext=(4.2, ya),
                    arrowprops=dict(arrowstyle="-|>", color=LINE, lw=1, ls="--", connectionstyle=f"arc3,rad={rad}"))
        ax.text(4.55 + abs(ya - yb) * 0.1, (ya + yb) / 2, label, fontsize=7, color=LINE, ha="left", va="center")
    include("Register Account", "Verify College Email")
    include("Submit Review", "Login")
    ax.text(5, 0.05, "Reconstructed from Experiments 1, 4 and 5 (the original Experiment 3 image was not supplied for this build)", ha="center", fontsize=8, color=LINE)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")


if __name__ == "__main__":
    architecture("architecture.png")
    usecase("use_case.png")
