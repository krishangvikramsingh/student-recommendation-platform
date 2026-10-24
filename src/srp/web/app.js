const CAMPUS = { lat: 19.1044, lon: 72.8365 };
const CATEGORY_NAMES = { pg_hostel: "PG / Hostel", restaurant: "Restaurant", stationery: "Stationery shop", sports: "Sports facility", event: "Event" };
const PRICE = ["Free", "Low", "Medium", "High"];
const ICONS = {
  pg_hostel: "M3 11l9-8 9 8M5 10v10h14V10M10 20v-6h4v6",
  restaurant: "M7 3v8M5 3v5a2 2 0 004 0V3M7 11v10M17 3c-2 2-2 6 0 8v10",
  stationery: "M4 20l1-4L16 5l3 3L8 19l-4 1zM14 7l3 3",
  sports: "M12 3a9 9 0 100 18 9 9 0 000-18zM3 12h18M12 3c3 3 3 15 0 18",
  event: "M4 6h16v14H4zM4 10h16M8 3v4M16 3v4",
  shield: "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM9 12l2 2 4-4",
  pin: "M12 21s7-6 7-11a7 7 0 10-14 0c0 5 7 11 7 11zM12 7.5a2.5 2.5 0 100 5 2.5 2.5 0 000-5z",
  chat: "M4 5h16v11H9l-5 4z",
  star: "M12 3l2.8 5.8 6.2.9-4.5 4.4 1.1 6.2L12 17.3 6.4 20.3l1.1-6.2L3 9.7l6.2-.9z",
  tag: "M3 12V3h9l9 9-9 9zM7.5 7.5h.01",
};
// The session lives in an HttpOnly cookie the page cannot read; only the display name and role are kept here.
const state = { signedIn: false, role: null, name: null, view: "search" };
const main = document.getElementById("main");
const nav = document.getElementById("nav");
const banner = document.getElementById("banner");

function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") el.className = value;
    else if (key.startsWith("on")) el.addEventListener(key.slice(2), value);
    else if (value !== false && value !== null && value !== undefined) el.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) el.append(child instanceof Node ? child : document.createTextNode(String(child ?? "")));
  return el;
}

function icon(name) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.8");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", ICONS[name]);
  svg.append(path);
  return svg;
}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", "X-Requested-With": "srp" };
  const response = await fetch(path, { method: options.method || "GET", headers, body: options.body ? JSON.stringify(options.body) : undefined });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && state.signedIn && data.error === "LoginRequired") {
      signOut(false);
      say("Your session ended. Please log in again.", "err");
    }
    const error = new Error(data.message || (response.status === 429 ? "Too many attempts. Please wait a moment." : "Request failed"));
    error.code = data.error;
    throw error;
  }
  return data;
}

function say(text, kind = "ok") {
  banner.replaceChildren(h("p", { class: "msg " + kind }, text));
}

const field = (label, control) => h("label", {}, label, control);
const option = (value, text, selected) => h("option", { value, selected: !!selected }, text);
const categorySelect = (id) => h("select", { id }, Object.entries(CATEGORY_NAMES).map(([v, t]) => option(v, t)));

function starRow(rating) {
  const filled = Math.round(rating);
  return h("span", { class: "stars", "aria-hidden": "true" }, "★".repeat(filled), h("span", { class: "off" }, "★".repeat(5 - filled)));
}

function ratingText(rating) {
  return rating > 0 ? `${rating.toFixed(1)} / 5` : "No ratings yet";
}

function chip(iconName, text) {
  return h("span", { class: "chip" }, iconName ? icon(iconName) : "", text);
}

function signOut(callApi = true) {
  if (callApi && state.signedIn) api("/logout", { method: "POST" }).catch(() => {});
  state.signedIn = false;
  state.role = state.name = null;
  show("search");
}

function renderNav() {
  const items = [["search", "Search"], ["events", "Events"]];
  if (state.signedIn) items.push(["foryou", "For you"], ["notifications", "Notifications"]);
  if (state.role === "admin") items.push(["admin", "Admin"]);
  if (state.signedIn) items.push(["settings", "Settings"]);
  items.push(state.signedIn ? ["logout", "Log out"] : ["account", "Log in / Register"]);
  nav.replaceChildren(...items.map(([key, text]) => h("button", { type: "button", "aria-current": key === state.view ? "page" : false, onclick: () => (key === "logout" ? signOut() : show(key)) }, text)));
}

function show(view, arg) {
  state.view = view;
  banner.replaceChildren();
  renderNav();
  const views = { settings: viewSettings, forgot: viewForgot, reset: viewReset, verify: viewVerify, check: viewCheckEmail, search: viewSearch, events: viewEvents, foryou: viewForYou, notifications: viewNotifications, account: viewAccount, admin: viewAdmin, detail: viewDetail };
  main.replaceChildren(h("p", { class: "meta loading", role: "status" }, "Loading..."));
  window.scrollTo({ top: 0 });
  Promise.resolve(views[view](arg)).catch((err) => say(err.message, "err"));
}

function listingCard(item) {
  const facts = [chip("star", ratingText(item.rating))];
  if (item.review_count !== undefined) facts.push(chip("chat", `${item.review_count} verified review(s)`));
  if (item.category !== "event") facts.push(chip("tag", `Cost: ${PRICE[item.price_level]}`));
  if (item.distance_km !== undefined) facts.push(chip("pin", `${item.distance_km} km away`));
  if (item.event_date) facts.push(chip("event", item.event_date));
  return h("article", { class: "card" },
    h("span", { class: "tag cat-" + item.category }, icon(item.category), CATEGORY_NAMES[item.category]),
    h("h3", { class: "name" }, item.name),
    h("div", {}, starRow(item.rating)),
    h("p", { class: "desc" }, item.description),
    h("div", { class: "facts" }, facts),
    h("div", { class: "push" }, h("button", { type: "button", class: "secondary", onclick: () => show("detail", item.id) }, "View details of " + item.name)));
}

function resultsBox(data) {
  if (!data.results.length) return h("p", { class: "msg" }, data.message || "No results.");
  return h("section", { class: "grid", "aria-label": "Results" }, data.results.map(listingCard));
}

function featureRow() {
  const items = [["shield", "Verified students only", "Reviews come from students whose college email has been checked."],
    ["chat", "Moderated reviews", "Every review is approved by an administrator before it counts."],
    ["pin", "Close to campus", "Results are sorted by distance, starting within 5 km."]];
  return h("section", { class: "features", "aria-label": "Why this platform" }, items.map(([i, t, d]) => h("div", { class: "feature" }, h("div", { class: "ico" }, icon(i)), h("h3", {}, t), h("p", {}, d))));
}

function viewSearch() {
  const out = h("div", { id: "results" });
  const form = h("form", { class: "card glass", "aria-label": "Search places" },
    h("div", { class: "row" }, field("Category", categorySelect("category")),
      field("Latitude", h("input", { id: "lat", type: "number", step: "any", value: CAMPUS.lat, required: true })),
      field("Longitude", h("input", { id: "lon", type: "number", step: "any", value: CAMPUS.lon, required: true })),
      field("Radius (km)", h("input", { id: "radius", type: "number", step: "any", min: "0.5", max: "100", value: "5" }))),
    h("div", { class: "row" },
      field("Maximum cost", h("select", { id: "price" }, option("", "Any"), PRICE.map((p, i) => option(i, p)))),
      field("Minimum rating", h("select", { id: "rating" }, option("", "Any"), [1, 2, 3, 4, 5].map((n) => option(n, n + " and above"))))),
    h("div", { class: "actions" },
      h("button", { type: "submit", class: "primary" }, "Search"),
      h("button", { type: "button", class: "secondary", onclick: () => { form.querySelector("#price").value = ""; form.querySelector("#rating").value = ""; form.querySelector("#radius").value = "5"; form.requestSubmit(); } }, "Reset filters"),
      h("button", { type: "button", class: "secondary", onclick: locate }, "Use my location")));
  function locate() {
    if (!navigator.geolocation) return say("Location is not available in this browser.", "err");
    navigator.geolocation.getCurrentPosition((pos) => { form.querySelector("#lat").value = pos.coords.latitude.toFixed(5); form.querySelector("#lon").value = pos.coords.longitude.toFixed(5); say("Location updated."); }, () => say("Location permission was denied. Enter coordinates manually.", "err"));
  }
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const q = new URLSearchParams({ category: form.querySelector("#category").value, lat: form.querySelector("#lat").value, lon: form.querySelector("#lon").value, radius: form.querySelector("#radius").value });
    if (form.querySelector("#price").value) q.set("max_price", form.querySelector("#price").value);
    if (form.querySelector("#rating").value) q.set("min_rating", form.querySelector("#rating").value);
    try { banner.replaceChildren(); out.replaceChildren(resultsBox(await api("/search?" + q))); } catch (err) { say(err.message, "err"); }
  });
  main.replaceChildren(
    h("section", { class: "hero" }, h("span", { class: "eyebrow" }, "For students new to the city"),
      h("h1", {}, "Find your place. ", h("span", { class: "grad" }, "Trusted by students.")),
      h("p", { class: "lede" }, "PGs, food, stationery, sports and events near your campus, rated by verified students.")),
    h("h2", { class: "section-title" }, "Search nearby places"),
    h("p", { class: "section-sub" }, "Choose a category, set your location and filter by cost and rating."),
    form, out, featureRow());
}

async function viewEvents() {
  const out = h("div");
  const form = h("form", { class: "card glass", "aria-label": "Filter events" },
    h("div", { class: "row" }, field("Event type", h("select", { id: "etype" }, option("", "All types"), ["Cultural", "Sports", "Technical"].map((t) => option(t, t)))),
      field("From date", h("input", { id: "efrom", type: "date" })), field("To date", h("input", { id: "eto", type: "date" }))),
    h("div", { class: "actions" }, h("button", { type: "submit", class: "primary" }, "Apply filters"), h("button", { type: "button", class: "secondary", onclick: () => { form.reset(); form.requestSubmit(); } }, "Reset filters")));
  async function load() {
    const q = new URLSearchParams();
    for (const [id, key] of [["etype", "event_type"], ["efrom", "date_from"], ["eto", "date_to"]]) if (form.querySelector("#" + id).value) q.set(key, form.querySelector("#" + id).value);
    out.replaceChildren(resultsBox(await api("/events?" + q)));
  }
  form.addEventListener("submit", (event) => { event.preventDefault(); load().catch((err) => say(err.message, "err")); });
  main.replaceChildren(h("h2", { class: "page-title" }, "Upcoming events"), h("p", { class: "section-sub" }, "College and city activities in date order."), form, out);
  await load();
}

async function viewDetail(id) {
  const item = await api("/listings/" + id);
  const details = Object.entries(item.details).map(([k, v]) => h("li", {}, h("b", {}, k.replaceAll("_", " ")), v));
  const reviews = item.reviews.length ? item.reviews.map((r) => h("article", { class: "card review" }, h("p", { class: "meta" }, h("strong", {}, r.author), ` rated ${r.rating} / 5 `, starRow(r.rating)), h("p", { class: "quote" }, r.comment),
    state.signedIn ? h("button", { type: "button", class: "secondary", onclick: () => reportReview(r.id) }, "Report this review") : "")) : [h("p", { class: "msg" }, "No published reviews yet.")];
  const children = [h("div", { class: "actions" }, h("button", { type: "button", class: "secondary", onclick: () => show("search") }, "Back to search")),
    h("section", { class: "card" }, h("div", { class: "detail-head" },
      h("div", {}, h("span", { class: "tag cat-" + item.category }, icon(item.category), CATEGORY_NAMES[item.category]), h("h2", { class: "page-title" }, item.name), h("p", { class: "desc" }, item.description), item.address ? h("p", { class: "meta" }, item.address) : ""),
      h("div", {}, h("div", { class: "big-score" }, item.rating > 0 ? item.rating.toFixed(1) : "–"), starRow(item.rating), h("p", { class: "meta" }, `Rating: ${ratingText(item.rating)} from ${item.review_count} verified review(s)`))),
      h("ul", { class: "kv" }, details)),
    h("h2", { class: "section-title" }, "Student reviews"), reviews];
  if (state.role === "student") {
    const form = h("form", { class: "card", "aria-label": "Write a review" }, h("h3", {}, "Write a review"),
      field("Rating", h("select", { id: "stars", required: true }, [5, 4, 3, 2, 1].map((n) => option(n, n + " star" + (n > 1 ? "s" : ""))))),
      field("Comment", h("textarea", { id: "comment", rows: "3", maxlength: "1000", required: true })), h("div", { class: "actions" }, h("button", { type: "submit", class: "primary" }, "Submit review")));
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      try { await api("/reviews", { method: "POST", body: { rec_id: id, rating: Number(form.querySelector("#stars").value), comment: form.querySelector("#comment").value } }); form.reset(); say("Review submitted. It will appear after administrator approval."); } catch (err) { say(err.message, "err"); }
    });
    children.push(form);
  } else if (!state.signedIn) children.push(h("p", { class: "msg" }, "Log in with your college email to write a review."));
  main.replaceChildren(...children);
}

async function reportReview(id) {
  const reason = prompt("Why are you reporting this review?");
  if (!reason) return;
  try { await api(`/reviews/${id}/report`, { method: "POST", body: { reason } }); say("Thanks. The review is now under review by an administrator."); } catch (err) { say(err.message, "err"); }
}

async function viewForYou() {
  const me = await api("/me");
  const out = h("div");
  const boxes = me.categories.map((c) => h("label", {}, h("input", { type: "checkbox", name: "pref", value: c, checked: me.preferences.includes(c) }), CATEGORY_NAMES[c]));
  const form = h("form", { class: "card", "aria-label": "Preferences" }, h("fieldset", {}, h("legend", {}, "What are you interested in?"), h("div", { class: "checks" }, boxes)), h("div", { class: "actions" }, h("button", { type: "submit", class: "primary" }, "Save and show recommendations")));
  async function load() { out.replaceChildren(resultsBox(await api(`/recommend?lat=${CAMPUS.lat}&lon=${CAMPUS.lon}`).then((d) => ({ results: d.results, message: "No recommendations match your preferences nearby." })))); }
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try { await api("/me/preferences", { method: "PUT", body: { categories: [...form.querySelectorAll("input:checked")].map((i) => i.value) } }); say("Preferences saved."); await load(); } catch (err) { say(err.message, "err"); }
  });
  main.replaceChildren(h("h2", { class: "page-title" }, "Recommended for you"), h("p", { class: "section-sub" }, "Ranked by your interests and distance from campus."), form, out);
  await load();
}

async function viewNotifications() {
  const [list, me] = await Promise.all([api("/notifications"), api("/me")]);
  const items = list.length ? list.map((n) => h("article", { class: "card" + (n.read ? "" : " unread") }, h("p", {}, h("span", { class: "status" }, n.category), n.read ? "" : h("strong", {}, "New: "), n.message),
    h("p", { class: "meta" }, n.created_at.replace("T", " ").slice(0, 16)), n.read ? "" : h("button", { type: "button", class: "secondary", onclick: async () => { await api(`/notifications/${n.id}/read`, { method: "POST" }); show("notifications"); } }, "Mark as read"))) : [h("p", { class: "msg" }, "No notifications yet.")];
  const names = ["event", "review", "moderation", "account"];
  const form = h("form", { class: "card", "aria-label": "Notification settings" }, h("fieldset", {}, h("legend", {}, "Turn off these notification types"), h("div", { class: "checks" }, names.map((c) => h("label", {}, h("input", { type: "checkbox", value: c, checked: me.disabled_notifications.includes(c) }), c)))), h("div", { class: "actions" }, h("button", { type: "submit", class: "primary" }, "Save settings")));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try { await api("/me/notification-settings", { method: "PUT", body: { disabled: [...form.querySelectorAll("input:checked")].map((i) => i.value) } }); say("Notification settings saved."); } catch (err) { say(err.message, "err"); }
  });
  main.replaceChildren(h("h2", { class: "page-title" }, "Notifications"), h("p", { class: "section-sub" }, "Events, review outcomes and moderation updates."), ...items, form);
}

async function viewAccount() {
  const colleges = await api("/colleges");
  const resend = h("div", { class: "actions", hidden: true });
  const login = h("form", { class: "card", "aria-label": "Log in" }, h("h2", {}, "Log in"), h("p", { class: "meta" }, "Welcome back."),
    field("College email", h("input", { id: "login-email", type: "email", required: true, autocomplete: "username" })),
    field("Password", h("input", { id: "login-password", type: "password", required: true, autocomplete: "current-password" })),
    h("div", { class: "actions" }, h("button", { type: "submit", class: "primary" }, "Log in"),
      h("button", { type: "button", class: "link", onclick: () => show("forgot", login.querySelector("#login-email").value) }, "Forgot password?")), resend);
  const register = h("form", { class: "card", "aria-label": "Register" }, h("h2", {}, "Create an account"), h("p", { class: "meta" }, "Use your college email. We will send a link to confirm it is yours."),
    field("Full name", h("input", { id: "reg-name", required: true, autocomplete: "name" })),
    field("College", h("select", { id: "reg-college", required: true }, colleges.map((c) => option(c.id, c.name)))),
    field("College email", h("input", { id: "reg-email", type: "email", required: true, autocomplete: "email" })),
    field("Password (8 or more characters)", h("input", { id: "reg-password", type: "password", minlength: "8", maxlength: "128", required: true, autocomplete: "new-password" })), h("div", { class: "actions" }, h("button", { type: "submit", class: "primary" }, "Register")));
  login.addEventListener("submit", async (event) => {
    event.preventDefault();
    resend.hidden = true;
    const email = login.querySelector("#login-email").value;
    try { await signIn(email, login.querySelector("#login-password").value); } catch (err) {
      say(err.message, "err");
      if (err.code === "EmailNotVerified") {
        resend.replaceChildren(h("button", { type: "button", class: "secondary", onclick: () => resendLink(email) }, "Send a new confirmation link"));
        resend.hidden = false;
      }
    }
  });
  register.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = register.querySelector("#reg-email").value;
    try {
      const made = await api("/register", { method: "POST", body: { name: register.querySelector("#reg-name").value, email, password: register.querySelector("#reg-password").value, college_id: register.querySelector("#reg-college").value } });
      if (made.verification_sent) return show("check", { email, devLink: made.dev_link });
      await signIn(email, register.querySelector("#reg-password").value);
      say("Account created. You are logged in.");
    } catch (err) { say(err.message, "err"); }
  });
  main.replaceChildren(h("h2", { class: "page-title" }, "Your account"), h("p", { class: "section-sub" }, "Students sign in with their college email."), h("div", { class: "row" }, login, register));
}

async function signIn(email, password) {
  const session = await api("/login", { method: "POST", body: { email, password } });
  state.signedIn = true; state.role = session.role; state.name = session.name;
  show(session.role === "admin" ? "admin" : "search");
  say(`Welcome, ${session.name}.`);
}

async function resendLink(email) {
  try { const out = await api("/email/resend", { method: "POST", body: { email } }); say(out.status); } catch (err) { say(err.message, "err"); }
}

// Development convenience: when the server runs on loopback with SRP_DEV_LINKS=1 it returns the emailed link so a
// local install works without an SMTP server. Production never sends this field.
const devLinkNote = (link) => (link ? h("p", { class: "msg" }, "Local mode, no email is sent. ", h("a", { href: link }, "Open the link from the email")) : "");

function viewCheckEmail({ email, devLink }) {
  main.replaceChildren(h("h2", { class: "page-title" }, "Check your email"),
    h("p", { class: "section-sub" }, `We sent a confirmation link to ${email}. It works once and expires in 24 hours.`),
    devLinkNote(devLink),
    h("div", { class: "actions" }, h("button", { type: "button", class: "secondary", onclick: () => resendLink(email) }, "Send it again"),
      h("button", { type: "button", class: "link", onclick: () => show("account") }, "Back to log in")));
}

function viewForgot(prefill) {
  const form = h("form", { class: "card", "aria-label": "Reset password" }, h("h2", {}, "Reset your password"), h("p", { class: "meta" }, "Enter your college email and we will send a reset link."),
    field("College email", h("input", { id: "forgot-email", type: "email", required: true, autocomplete: "username", value: typeof prefill === "string" ? prefill : "" })),
    h("div", { class: "actions" }, h("button", { type: "submit", class: "primary" }, "Send reset link"), h("button", { type: "button", class: "link", onclick: () => show("account") }, "Back to log in")));
  const note = h("div");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const out = await api("/password/forgot", { method: "POST", body: { email: form.querySelector("#forgot-email").value } });
      say(out.status);
      note.replaceChildren(devLinkNote(out.dev_link));
    } catch (err) { say(err.message, "err"); }
  });
  main.replaceChildren(h("h2", { class: "page-title" }, "Forgot password"), h("p", { class: "section-sub" }, "Links work once and expire after an hour."), form, note);
}

function viewReset(token) {
  const form = h("form", { class: "card", "aria-label": "Choose a new password" }, h("h2", {}, "Choose a new password"),
    field("New password (8 to 128 characters)", h("input", { id: "new-pw", type: "password", minlength: "8", maxlength: "128", required: true, autocomplete: "new-password" })),
    field("Repeat new password", h("input", { id: "new-pw2", type: "password", minlength: "8", maxlength: "128", required: true, autocomplete: "new-password" })),
    h("div", { class: "actions" }, h("button", { type: "submit", class: "primary" }, "Update password")));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (form.querySelector("#new-pw").value !== form.querySelector("#new-pw2").value) return say("The two passwords do not match.", "err");
    try {
      const out = await api("/password/reset", { method: "POST", body: { token, password: form.querySelector("#new-pw").value } });
      show("account");
      say(out.status);
    } catch (err) { say(err.message, "err"); }
  });
  main.replaceChildren(h("h2", { class: "page-title" }, "Reset password"), h("p", { class: "section-sub" }, "Pick something you do not use anywhere else."), form);
}

async function viewVerify(token) {
  main.replaceChildren(h("h2", { class: "page-title" }, "Confirming your email"), h("p", { class: "meta" }, "One moment..."));
  try {
    await api("/email/verify", { method: "POST", body: { token } });
    main.replaceChildren(h("h2", { class: "page-title" }, "Email confirmed"), h("p", { class: "section-sub" }, "Your college email is verified. You can log in now."),
      h("div", { class: "actions" }, h("button", { type: "button", class: "primary", onclick: () => show("account") }, "Log in")));
  } catch (err) {
    main.replaceChildren(h("h2", { class: "page-title" }, "That link did not work"), h("p", { class: "section-sub" }, err.message),
      h("div", { class: "actions" }, h("button", { type: "button", class: "secondary", onclick: () => show("account") }, "Back to log in")));
  }
}

function viewSettings() {
  const form = h("form", { class: "card", "aria-label": "Change password" }, h("h2", {}, "Change password"), h("p", { class: "meta" }, "Other devices will be signed out."),
    field("Current password", h("input", { id: "cur-pw", type: "password", required: true, autocomplete: "current-password" })),
    field("New password (8 to 128 characters)", h("input", { id: "chg-pw", type: "password", minlength: "8", maxlength: "128", required: true, autocomplete: "new-password" })),
    h("div", { class: "actions" }, h("button", { type: "submit", class: "primary" }, "Update password")));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const out = await api("/me/password", { method: "POST", body: { current_password: form.querySelector("#cur-pw").value, new_password: form.querySelector("#chg-pw").value } });
      form.reset();
      say(out.status);
    } catch (err) { say(err.message, "err"); }
  });
  main.replaceChildren(h("h2", { class: "page-title" }, "Settings"), h("p", { class: "section-sub" }, `Signed in as ${state.name}.`), form);
}

const tile = (num, label, hot) => h("div", { class: "tile" + (hot ? " hot" : "") }, h("div", { class: "num" }, num), h("div", { class: "lab" }, label));
const statusPill = (text, cls) => h("span", { class: "status " + cls }, text);

async function viewAdmin() {
  const [queue, users, audit, cities, colleges] = await Promise.all([api("/admin/reviews"), api("/admin/users"), api("/admin/audit"), api("/cities"), api("/colleges")]);
  const act = (path, body) => async () => { try { await api(path, { method: "POST", body }); show("admin"); } catch (err) { say(err.message, "err"); } };
  const reviewCards = queue.length ? queue.map((r) => h("article", { class: "card review" },
    h("p", {}, statusPill(r.status, r.status === "Pending" ? "pending" : "review"), h("strong", {}, r.listing), ` by ${r.author}: ${r.rating} / 5`), h("p", { class: "quote" }, r.comment),
    r.reports.length ? h("p", { class: "meta" }, "Reports: " + r.reports.join("; ")) : "",
    h("div", { class: "actions" }, h("button", { type: "button", class: "primary", onclick: act(`/reviews/${r.id}/validate`, { approve: true }) }, "Approve / keep"), h("button", { type: "button", class: "danger", onclick: act(`/reviews/${r.id}/validate`, { approve: false }) }, "Reject / remove")))) : [h("p", { class: "msg" }, "No reviews are waiting for moderation.")];
  const userRows = users.map((u) => h("tr", {}, h("td", {}, u.name), h("td", {}, u.email), h("td", {}, statusPill(u.verified ? "Verified" : "Unverified", u.verified ? "verified" : "pending")), h("td", {}, statusPill(u.suspended ? "Suspended" : "Active", u.suspended ? "suspended" : "active")),
    h("td", {}, h("div", { class: "actions" }, !u.verified ? h("button", { type: "button", class: "secondary", onclick: act(`/admin/users/${u.id}/verify`, {}) }, "Verify") : "", u.suspended ? h("button", { type: "button", class: "secondary", onclick: act(`/admin/users/${u.id}/reinstate`, {}) }, "Reinstate " + u.name) : h("button", { type: "button", class: "danger", onclick: act(`/admin/users/${u.id}/suspend`, {}) }, "Suspend " + u.name)))));
  const listingForm = h("form", { class: "card", "aria-label": "Add listing" }, h("h3", {}, "Add a listing"),
    h("div", { class: "row" }, field("Name", h("input", { id: "l-name", required: true })), field("Category", categorySelect("l-cat")), field("City", h("select", { id: "l-city" }, cities.map((c) => option(c.id, c.name))))),
    h("div", { class: "row" }, field("Latitude", h("input", { id: "l-lat", type: "number", step: "any", required: true, value: CAMPUS.lat })), field("Longitude", h("input", { id: "l-lon", type: "number", step: "any", required: true, value: CAMPUS.lon })),
      field("Cost level", h("select", { id: "l-price" }, PRICE.map((p, i) => option(i, p)))), field("Event date (events only)", h("input", { id: "l-date", type: "date" }))),
    field("Description", h("input", { id: "l-desc" })), h("div", { class: "actions" }, h("button", { type: "submit", class: "primary" }, "Add listing")));
  listingForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const f = (id) => listingForm.querySelector("#" + id).value;
    const body = { name: f("l-name"), category: f("l-cat"), city_id: f("l-city"), lat: Number(f("l-lat")), lon: Number(f("l-lon")), price_level: Number(f("l-price")), description: f("l-desc") };
    if (body.category === "event") { body.event_date = f("l-date"); body.details = { event_type: "Cultural" }; }
    try { await api("/admin/listings", { method: "POST", body }); say("Listing added."); listingForm.reset(); } catch (err) { say(err.message, "err"); }
  });
  const collegeForm = h("form", { class: "card", "aria-label": "Add college" }, h("h3", {}, "Add a college"),
    h("div", { class: "row" }, field("College name", h("input", { id: "c-name", required: true })), field("Email domain", h("input", { id: "c-domain", required: true, placeholder: "example.edu.in" })), field("City", h("select", { id: "c-city" }, cities.map((c) => option(c.id, c.name))))), h("div", { class: "actions" }, h("button", { type: "submit", class: "primary" }, "Add college")));
  collegeForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const f = (id) => collegeForm.querySelector("#" + id).value;
    try { await api("/admin/colleges", { method: "POST", body: { name: f("c-name"), domain: f("c-domain"), city_id: f("c-city") } }); say("College added."); collegeForm.reset(); } catch (err) { say(err.message, "err"); }
  });
  const cityForm = h("form", { class: "card", "aria-label": "Add city" }, h("h3", {}, "Add a city"),
    h("div", { class: "row" }, field("City name", h("input", { id: "ct-name", required: true })), field("State", h("input", { id: "ct-state", required: true }))), h("div", { class: "actions" }, h("button", { type: "submit", class: "primary" }, "Add city")));
  cityForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try { await api("/admin/cities", { method: "POST", body: { name: cityForm.querySelector("#ct-name").value, state: cityForm.querySelector("#ct-state").value } }); say("City added."); cityForm.reset(); } catch (err) { say(err.message, "err"); }
  });
  const auditRows = audit.slice(0, 15).map((e) => h("tr", {}, h("td", {}, e.at.replace("T", " ").slice(0, 19)), h("td", {}, e.actor), h("td", {}, e.action), h("td", {}, e.target)));
  const table = (head, rows, cap) => h("div", { class: "table-wrap" }, h("table", {}, cap ? h("caption", {}, cap) : "", h("thead", {}, h("tr", {}, head.map((t) => h("th", { scope: "col" }, t)))), h("tbody", {}, rows)));
  main.replaceChildren(
    h("h2", { class: "page-title" }, "Administrator dashboard"), h("p", { class: "section-sub" }, "Moderate reviews, manage students and keep the catalogue accurate."),
    h("div", { class: "tiles" }, tile(queue.length, "Reviews awaiting moderation", queue.length > 0), tile(users.length, "Students"), tile(users.filter((u) => u.suspended).length, "Suspended accounts"), tile(`${colleges.length} / ${cities.length}`, "Colleges / cities")),
    h("h3", { class: "section-title" }, "Reviews awaiting moderation"), ...reviewCards,
    h("h3", { class: "section-title" }, "Students"), table(["Name", "Email", "Verification", "Status", "Actions"], userRows),
    h("h3", { class: "section-title" }, "Manage the catalogue"), listingForm, collegeForm, cityForm,
    h("h3", { class: "section-title" }, "Recent audit log"), table(["Time", "Actor", "Action", "Target"], auditRows));
}

async function boot() {
  try {
    const me = await api("/me");
    state.signedIn = true; state.role = me.role; state.name = me.name;
  } catch { /* not signed in */ }
  const params = new URLSearchParams(location.search);
  const link = [["verify", "verify"], ["reset", "reset"]].find(([key]) => params.get(key));
  history.replaceState(null, "", location.pathname); // keep one-time tokens out of history and the address bar
  if (link) show(link[1], params.get(link[0]));
  else show("search");
}
boot();
