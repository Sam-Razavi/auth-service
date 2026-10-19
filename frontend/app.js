/* Auth Service frontend — dependency-free single-page app.
 * Talks to the API on the same origin by default; set window.AUTH_API_BASE
 * before this script loads to point it at another host. */
(() => {
  "use strict";

  const API_BASE = (window.AUTH_API_BASE || "").replace(/\/$/, "");
  const ROLES = ["admin", "moderator", "user"];
  const STORE_KEY = "auth-service.tokens";

  // ---------- Icons ----------
  const icon = (d, size = 18) =>
    `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
  const I = {
    mail: icon('<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>'),
    lock: icon('<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>'),
    key: icon('<circle cx="8" cy="15" r="4"/><path d="m10.8 12.2 9.2-9.2M17 6l3 3M14 9l2 2"/>'),
    eye: icon('<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>'),
    eyeOff: icon('<path d="M3 3l18 18M10.6 5.1A10.5 10.5 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-3 3.9M6.6 6.6A17 17 0 0 0 2 12s3.5 7 10 7a10 10 0 0 0 5.4-1.6"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>'),
    check: icon('<path d="M20 6 9 17l-5-5"/>'),
    x: icon('<path d="M18 6 6 18M6 6l12 12"/>'),
    info: icon('<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>'),
    alert: icon('<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>'),
    shield: icon('<path d="M12 3l7 3v5c0 4.6-3 8.4-7 9.6C8 19.4 5 15.6 5 11V6z"/><path d="m9 12 2 2 4-4"/>'),
    user: icon('<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>'),
    users: icon('<circle cx="9" cy="8" r="4"/><path d="M1 21a8 8 0 0 1 16 0M16 4a4 4 0 0 1 0 8M23 21a8 8 0 0 0-5-7.4"/>'),
    clock: icon('<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>'),
    refresh: icon('<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>'),
    logout: icon('<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>'),
    globe: icon('<circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20"/>'),
    copy: icon('<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>'),
    activity: icon('<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>'),
    zap: icon('<path d="M13 2 3 14h9l-1 8 10-12h-9z"/>'),
    search: icon('<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>'),
    trash: icon('<path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>'),
    github: '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 .5a11.5 11.5 0 0 0-3.6 22.4c.6.1.8-.3.8-.6v-2c-3.2.7-3.9-1.5-3.9-1.5-.5-1.3-1.3-1.7-1.3-1.7-1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.7-1.6-2.6-.3-5.3-1.3-5.3-5.7 0-1.3.5-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.2 1.2a11 11 0 0 1 5.8 0C17.3 4.8 18.3 5.1 18.3 5.1c.6 1.6.2 2.8.1 3.1.8.8 1.2 1.9 1.2 3.1 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.2c0 .3.2.7.8.6A11.5 11.5 0 0 0 12 .5z"/></svg>',
    google: '<svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.4h6.5a5.6 5.6 0 0 1-2.4 3.6v3h3.9c2.2-2.1 3.5-5.1 3.5-8.7z"/><path fill="#34A853" d="M12 24c3.2 0 6-1.1 8-2.9l-3.9-3c-1.1.7-2.5 1.2-4.1 1.2-3.1 0-5.8-2.1-6.7-5H1.3v3.1A12 12 0 0 0 12 24z"/><path fill="#FBBC05" d="M5.3 14.3a7.2 7.2 0 0 1 0-4.6V6.6H1.3a12 12 0 0 0 0 10.8z"/><path fill="#EA4335" d="M12 4.8c1.8 0 3.3.6 4.6 1.8l3.4-3.4A12 12 0 0 0 1.3 6.6l4 3.1c.9-2.8 3.6-4.9 6.7-4.9z"/></svg>',
  };

  // ---------- Helpers ----------
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const esc = (v) =>
    String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const PASSWORD_RE = /^(?=.*[A-Za-z])(?=.*[\d\W]).{8,}$/; // mirrors app/schemas/user.py

  const tokens = {
    get() {
      try { return JSON.parse(localStorage.getItem(STORE_KEY)) || null; } catch { return null; }
    },
    set(pair) {
      try { localStorage.setItem(STORE_KEY, JSON.stringify(pair)); } catch { /* storage unavailable */ }
    },
    clear() {
      try { localStorage.removeItem(STORE_KEY); } catch { /* storage unavailable */ }
    },
  };

  function decodeJwt(token) {
    try {
      const part = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
      return JSON.parse(atob(part.padEnd(part.length + ((4 - (part.length % 4)) % 4), "=")));
    } catch {
      return {};
    }
  }

  class ApiError extends Error {
    constructor(status, detail) {
      super(detail);
      this.status = status;
    }
  }

  let refreshing = null;
  async function refreshTokens() {
    const current = tokens.get();
    if (!current?.refresh_token) throw new ApiError(401, "Not signed in");
    refreshing ??= request("/auth/refresh", { method: "POST", body: { refresh_token: current.refresh_token } })
      .then((pair) => { tokens.set(pair); return pair; })
      .finally(() => { refreshing = null; });
    return refreshing;
  }

  async function request(path, { method = "GET", body, auth = false, retry = true } = {}) {
    const headers = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (auth) {
      const t = tokens.get();
      if (!t?.access_token) throw new ApiError(401, "Not signed in");
      headers.Authorization = `Bearer ${t.access_token}`;
    }
    let res;
    try {
      res = await fetch(API_BASE + path, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
    } catch {
      throw new ApiError(0, "Can't reach the auth service. Is it running?");
    }
    // HTTPBearer answers 403 when the header is missing; treat both as "session expired".
    if (auth && retry && (res.status === 401 || res.status === 403)) {
      try {
        await refreshTokens();
      } catch {
        tokens.clear();
        throw new ApiError(401, "Your session has expired. Please sign in again.");
      }
      return request(path, { method, body, auth, retry: false });
    }
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = typeof data.detail === "string" ? data.detail : `Request failed (${res.status})`;
      throw new ApiError(res.status, detail);
    }
    return data;
  }

  // ---------- Toasts ----------
  function toast(message, kind = "info") {
    const el = document.createElement("div");
    el.className = `toast ${kind}`;
    el.innerHTML = `${kind === "ok" ? I.check : kind === "err" ? I.alert : I.info}<span>${esc(message)}</span>`;
    $("#toasts").appendChild(el);
    setTimeout(() => { el.classList.add("out"); setTimeout(() => el.remove(), 260); }, 4200);
  }

  // ---------- Form building blocks ----------
  const field = ({ name, label, type = "text", placeholder = "", lead, autocomplete, extra = "", value = "" }) => `
    <div class="field">
      <label for="${name}">${label}${extra}</label>
      <div class="input-wrap">
        ${(lead || "").replace("<svg", '<svg class="lead"')}
        <input class="input" id="${name}" name="${name}" type="${type}" placeholder="${esc(placeholder)}"
          ${autocomplete ? `autocomplete="${autocomplete}"` : ""} value="${esc(value)}" required />
        ${type === "password" ? `<button type="button" class="reveal" data-reveal="${name}" aria-label="Show password">${I.eye}</button>` : ""}
      </div>
    </div>`;

  const strengthMeter = (forId) => `
    <div data-strength-for="${forId}">
      <div class="strength"><span></span><span></span><span></span><span></span></div>
      <ul class="rules">
        <li data-rule="len">At least 8 characters</li>
        <li data-rule="letter">Contains a letter</li>
        <li data-rule="other">Contains a number or symbol</li>
      </ul>
    </div>`;

  function wireForm(root) {
    $$("[data-reveal]", root).forEach((btn) =>
      btn.addEventListener("click", () => {
        const input = $(`#${btn.dataset.reveal}`, root);
        const show = input.type === "password";
        input.type = show ? "text" : "password";
        btn.innerHTML = show ? I.eyeOff : I.eye;
      })
    );
    $$("[data-strength-for]", root).forEach((meter) => {
      const input = $(`#${meter.dataset.strengthFor}`, root);
      const bars = $$(".strength span", meter);
      const colors = ["#f43f5e", "#f59e0b", "#06b6d4", "#22c55e"];
      const update = () => {
        const v = input.value;
        const rules = { len: v.length >= 8, letter: /[A-Za-z]/.test(v), other: /[\d\W]/.test(v) };
        Object.entries(rules).forEach(([k, ok]) => $(`[data-rule="${k}"]`, meter).classList.toggle("ok", ok));
        let score = Object.values(rules).filter(Boolean).length;
        if (score === 3 && v.length >= 12 && /\d/.test(v) && /[^\w\s]/.test(v)) score = 4;
        if (!v) score = 0;
        bars.forEach((b, i) => (b.style.background = i < score ? colors[score - 1] : ""));
      };
      input.addEventListener("input", update);
      update();
    });
  }

  async function withBusy(button, fn) {
    const html = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `<span class="spinner"></span>${button.dataset.busy || "Working…"}`;
    try {
      return await fn();
    } finally {
      button.disabled = false;
      button.innerHTML = html;
    }
  }

  function onSubmit(form, handler) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const data = Object.fromEntries(new FormData(form).entries());
      const btn = $("button[type=submit]", form);
      try {
        await withBusy(btn, () => handler(data));
      } catch (err) {
        toast(err.message, "err");
      }
    });
  }

  // ---------- Layout pieces ----------
  const hero = (title, sub) => `
    <section class="hero">
      <span class="eyebrow"><span class="dot"></span>Production-grade auth for every app</span>
      <h1>${title}</h1>
      <p>${sub}</p>
      <div class="features">
        <span class="feature">${I.zap}JWT + refresh rotation</span>
        <span class="feature">${I.shield}Account lockout</span>
        <span class="feature">${I.users}Role-based access</span>
        <span class="feature">${I.globe}GitHub & Google OAuth</span>
      </div>
    </section>`;

  const oauthButtons = () => `
    <div class="divider">or continue with</div>
    <div class="oauth">
      <a class="btn btn-ghost" href="${API_BASE}/oauth/github">${I.github}GitHub</a>
      <a class="btn btn-ghost" href="${API_BASE}/oauth/google">${I.google}Google</a>
    </div>`;

  function renderNav(route) {
    const signedIn = !!tokens.get();
    const link = (href, label, ico) =>
      `<a href="#/${href}" class="${route === href ? "active" : ""}">${ico ? ico.replace("<svg", '<svg style="vertical-align:-4px;margin-right:6px"') : ""}<span class="lbl">${label}</span></a>`;
    $("#nav").innerHTML = signedIn
      ? link("dashboard", "Dashboard", I.user) +
        (state.user?.roles?.includes("admin") ? link("admin", "Admin", I.users) : "") +
        `<button id="nav-logout">${I.logout.replace("<svg", '<svg style="vertical-align:-4px;margin-right:6px"')}<span class="lbl">Sign out</span></button>`
      : link("login", "Sign in") + link("register", "Create account");
    $("#nav-logout")?.addEventListener("click", logout);
  }

  // ---------- Views ----------
  const state = { user: null, timer: null };

  const views = {
    login() {
      return {
        html: `
        <div class="center"><div class="split fade-in">
          ${hero('Sign in to<br/><span class="gradient">everything.</span>', "One account for ApplyLuma, Rostid and every app that comes next. Secure sessions, single sign-on and fine-grained roles — out of the box.")}
          <div class="card glow auth-card">
            <h2>Welcome back</h2>
            <p class="sub">Sign in with your email and password.</p>
            <form id="f" novalidate>
              ${field({ name: "email", label: "Email", type: "email", placeholder: "you@company.com", lead: I.mail, autocomplete: "email" })}
              ${field({ name: "password", label: "Password", type: "password", placeholder: "••••••••", lead: I.lock, autocomplete: "current-password", extra: '<a href="#/forgot-password">Forgot?</a>' })}
              <button class="btn btn-primary" type="submit" data-busy="Signing in…">Sign in</button>
            </form>
            ${oauthButtons()}
            <p class="form-foot">New here? <a href="#/register">Create an account</a></p>
          </div>
        </div></div>`,
        mount(root) {
          onSubmit($("#f", root), async ({ email, password }) => {
            tokens.set(await request("/auth/login", { method: "POST", body: { email, password } }));
            toast("Signed in successfully", "ok");
            go("dashboard");
          });
        },
      };
    },

    register() {
      return {
        html: `
        <div class="center"><div class="split fade-in">
          ${hero('Create your<br/><span class="gradient">universal account.</span>', "Register once and sign in anywhere the auth service is trusted. We'll send a verification link to your inbox.")}
          <div class="card glow auth-card">
            <h2>Create account</h2>
            <p class="sub">It takes less than a minute.</p>
            <form id="f" novalidate>
              ${field({ name: "email", label: "Email", type: "email", placeholder: "you@company.com", lead: I.mail, autocomplete: "email" })}
              ${field({ name: "password", label: "Password", type: "password", placeholder: "Create a strong password", lead: I.lock, autocomplete: "new-password" })}
              <div style="margin:-6px 0 20px">${strengthMeter("password")}</div>
              <button class="btn btn-primary" type="submit" data-busy="Creating account…">Create account</button>
            </form>
            ${oauthButtons()}
            <p class="form-foot">Already registered? <a href="#/login">Sign in</a></p>
          </div>
        </div></div>`,
        mount(root) {
          onSubmit($("#f", root), async ({ email, password }) => {
            if (!PASSWORD_RE.test(password)) throw new Error("Password doesn't meet the requirements yet.");
            await request("/auth/register", { method: "POST", body: { email, password } });
            tokens.set(await request("/auth/login", { method: "POST", body: { email, password } }));
            toast("Account created — check your inbox to verify your email", "ok");
            go("dashboard");
          });
        },
      };
    },

    "forgot-password"() {
      return {
        html: `
        <div class="center fade-in"><div class="card glow auth-card">
          <div class="status-icon wait">${icon('<circle cx="8" cy="15" r="4"/><path d="m10.8 12.2 9.2-9.2M17 6l3 3M14 9l2 2"/>', 28)}</div>
          <h2 style="text-align:center">Forgot your password?</h2>
          <p class="sub" style="text-align:center">Enter your email and we'll send you a one-hour reset link.</p>
          <div id="done"></div>
          <form id="f" novalidate>
            ${field({ name: "email", label: "Email", type: "email", placeholder: "you@company.com", lead: I.mail, autocomplete: "email" })}
            <button class="btn btn-primary" type="submit" data-busy="Sending…">Send reset link</button>
          </form>
          <p class="form-foot"><a href="#/login">← Back to sign in</a></p>
        </div></div>`,
        mount(root) {
          onSubmit($("#f", root), async ({ email }) => {
            const res = await request("/auth/forgot-password", { method: "POST", body: { email } });
            $("#done", root).innerHTML = `<div class="notice ok">${I.check}<span>${esc(res.message)}</span></div>`;
          });
        },
      };
    },

    "reset-password"(params) {
      const token = params.get("token") || "";
      return {
        html: `
        <div class="center fade-in"><div class="card glow auth-card">
          <h2>Choose a new password</h2>
          <p class="sub">Resetting signs you out of every device.</p>
          ${token ? "" : `<div class="notice warn">${I.alert}<span>No reset token found in the link. Paste it below.</span></div>`}
          <form id="f" novalidate>
            ${token ? `<input type="hidden" name="token" value="${esc(token)}"/>` : field({ name: "token", label: "Reset token", placeholder: "Token from the email", lead: I.key })}
            ${field({ name: "new_password", label: "New password", type: "password", placeholder: "Create a strong password", lead: I.lock, autocomplete: "new-password" })}
            <div style="margin:-6px 0 20px">${strengthMeter("new_password")}</div>
            <button class="btn btn-primary" type="submit" data-busy="Updating…">Update password</button>
          </form>
        </div></div>`,
        mount(root) {
          onSubmit($("#f", root), async ({ token, new_password }) => {
            if (!PASSWORD_RE.test(new_password)) throw new Error("Password doesn't meet the requirements yet.");
            await request("/auth/reset-password", { method: "POST", body: { token, new_password } });
            tokens.clear();
            toast("Password updated — sign in with your new password", "ok");
            go("login");
          });
        },
      };
    },

    "verify-email"(params) {
      const token = params.get("token") || "";
      return {
        html: `
        <div class="center fade-in"><div class="card glow auth-card" style="text-align:center" id="box">
          <div class="status-icon wait"><span class="spinner" style="width:26px;height:26px;border-width:3px;border-radius:50%;border-style:solid;border-color:rgba(167,139,250,.3);border-top-color:#a78bfa;animation:spin .7s linear infinite;display:block"></span></div>
          <h2>Verifying your email…</h2>
          <p class="sub">Hang tight, this only takes a second.</p>
        </div></div>`,
        async mount(root) {
          const box = $("#box", root);
          const show = (ok, title, msg) => {
            box.innerHTML = `
              <div class="status-icon ${ok ? "ok" : "err"}">${icon(ok ? '<path d="M20 6 9 17l-5-5"/>' : '<path d="M18 6 6 18M6 6l12 12"/>', 30)}</div>
              <h2>${title}</h2><p class="sub">${esc(msg)}</p>
              <a class="btn btn-primary" href="#/${tokens.get() ? "dashboard" : "login"}">Continue</a>`;
          };
          if (!token) return show(false, "Missing token", "This verification link is incomplete.");
          try {
            const res = await request(`/auth/verify-email/${encodeURIComponent(token)}`, { method: "POST" });
            show(true, "Email verified", res.message);
          } catch (err) {
            show(false, "Verification failed", err.message);
          }
        },
      };
    },

    dashboard() {
      if (!tokens.get()) return redirect("login");
      return {
        html: `<div id="dash-root"><div class="center"><span class="spinner" style="width:30px;height:30px;border:3px solid rgba(255,255,255,.15);border-top-color:#a78bfa;border-radius:50%;animation:spin .7s linear infinite"></span></div></div>`,
        async mount(root) {
          const user = await loadUser();
          if (!user) return;
          renderNav("dashboard");
          const initial = (user.email[0] || "?").toUpperCase();
          const created = new Date(user.created_at);
          $("#dash-root", root).innerHTML = `
          <div class="fade-in">
            <div class="page-head">
              <div><h1>Hello, ${esc(user.email.split("@")[0])} 👋</h1><p>Here's everything about your account and current session.</p></div>
              <div class="btn-row">
                <button class="btn btn-ghost btn-sm" id="b-refresh">${I.refresh}Rotate tokens</button>
                <button class="btn btn-danger btn-sm" id="b-logout-all">${I.logout}Sign out everywhere</button>
              </div>
            </div>

            ${user.is_verified ? "" : `
            <div class="notice warn">${I.mail}<span style="flex:1">Your email isn't verified yet. Check your inbox for the verification link.</span>
              <button class="btn btn-ghost btn-sm" id="b-resend">Resend email</button></div>`}

            <div class="dash">
              <section class="card span-7">
                <div class="card-head"><div class="title"><span class="ico">${I.user}</span><h3>Profile</h3></div></div>
                <div class="profile">
                  <div class="avatar">${esc(initial)}</div>
                  <div style="min-width:0">
                    <div class="email">${esc(user.email)}</div>
                    <div class="badges">
                      ${user.is_verified ? `<span class="badge ok">${I.check.replace(/18/g, "13")}Verified</span>` : `<span class="badge warn">Unverified</span>`}
                      ${user.is_active ? `<span class="badge ok">Active</span>` : `<span class="badge off">Deactivated</span>`}
                      ${(user.roles.length ? user.roles : ["no roles"]).map((r) => `<span class="badge role-${esc(r)}">${esc(r)}</span>`).join("")}
                    </div>
                  </div>
                </div>
                <dl class="kv">
                  <dt>User ID</dt><dd class="mono" title="${esc(user.id)}">${esc(user.id)}</dd>
                  <dt>Member since</dt><dd>${created.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })}</dd>
                  <dt>Token type</dt><dd>Bearer · HS256</dd>
                </dl>
              </section>

              <section class="card span-5">
                <div class="card-head"><div class="title"><span class="ico">${I.clock}</span><h3>Current session</h3></div><span class="badge ok" id="sess-badge">Live</span></div>
                <div class="session">
                  <div class="ring">
                    <svg width="118" height="118" viewBox="0 0 118 118">
                      <defs><linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#8b5cf6"/><stop offset="1" stop-color="#06b6d4"/></linearGradient></defs>
                      <circle class="track" cx="59" cy="59" r="50" fill="none" stroke-width="10"/>
                      <circle class="bar" id="ring-bar" cx="59" cy="59" r="50" fill="none" stroke-width="10" stroke-dasharray="314.16" stroke-dashoffset="0"/>
                    </svg>
                    <div class="label"><div><b id="ring-time">--:--</b><small>remaining</small></div></div>
                  </div>
                  <div class="session-info">
                    <p>Access tokens are short-lived. When this one expires the app silently rotates your refresh token.</p>
                    <button class="btn btn-ghost btn-sm" id="b-copy">${I.copy}Copy access token</button>
                  </div>
                </div>
                <div class="token-box" id="token-box"></div>
              </section>

              <section class="card span-6">
                <div class="card-head"><div class="title"><span class="ico">${I.lock}</span><h3>Set a password</h3></div></div>
                <p class="sub" style="margin:-6px 0 18px">Signed up with GitHub or Google? Add a password so you can sign in with email too.</p>
                <form id="f-setpw" novalidate>
                  ${field({ name: "new_password", label: "New password", type: "password", placeholder: "Create a strong password", lead: I.lock, autocomplete: "new-password" })}
                  <div style="margin:-6px 0 18px">${strengthMeter("new_password")}</div>
                  <button class="btn btn-primary" type="submit" data-busy="Saving…">Save password</button>
                </form>
                <p class="form-foot" style="margin-top:14px;font-size:13px">Already have one? <a href="#/forgot-password">Reset it by email</a></p>
              </section>

              <section class="card span-6">
                <div class="card-head"><div class="title"><span class="ico">${I.activity}</span><h3>Service status</h3></div><span class="badge" id="health-badge">Checking…</span></div>
                <div class="checks" id="checks"></div>
                <div class="divider" style="margin:20px 0 14px">security</div>
                <div class="checks">
                  <div class="check"><span class="left">${I.shield}Lockout after 5 failed logins</span><span class="badge ok">On</span></div>
                  <div class="check"><span class="left">${I.refresh}Refresh-token rotation</span><span class="badge ok">On</span></div>
                </div>
              </section>
            </div>
          </div>`;
          wireForm(root);
          startSessionTimer();
          renderHealthCard();

          $("#b-refresh").addEventListener("click", (e) =>
            withBusy(e.currentTarget, async () => {
              await refreshTokens().then(() => toast("New token pair issued — old refresh token revoked", "ok")).catch((err) => toast(err.message, "err"));
              startSessionTimer();
            })
          );
          $("#b-logout-all").addEventListener("click", async (e) => {
            if (!confirm("Sign out of every device? All refresh tokens will be revoked.")) return;
            await withBusy(e.currentTarget, async () => {
              try {
                await request("/auth/logout-all", { method: "POST", auth: true });
              } catch (err) {
                return toast(err.message, "err");
              }
              tokens.clear();
              state.user = null;
              toast("Signed out of all devices", "ok");
              go("login");
            });
          });
          $("#b-copy").addEventListener("click", async () => {
            try {
              await navigator.clipboard.writeText(tokens.get().access_token);
              toast("Access token copied to clipboard", "ok");
            } catch {
              toast("Clipboard unavailable in this browser", "err");
            }
          });
          $("#b-resend")?.addEventListener("click", (e) =>
            withBusy(e.currentTarget, async () => {
              const res = await request("/auth/verify-email/resend", { method: "POST", body: { email: user.email } }).catch((err) => ({ message: err.message }));
              toast(res.message, "info");
            })
          );
          onSubmit($("#f-setpw", root), async ({ new_password }) => {
            if (!PASSWORD_RE.test(new_password)) throw new Error("Password doesn't meet the requirements yet.");
            const res = await request("/auth/set-password", { method: "POST", auth: true, body: { new_password } });
            toast(res.message, "ok");
            $("#f-setpw").reset();
          });
        },
      };
    },

    admin() {
      if (!tokens.get()) return redirect("login");
      return {
        html: `<div id="admin-root"></div>`,
        async mount(root) {
          const me = await loadUser();
          if (!me) return;
          renderNav("admin");
          if (!me.roles.includes("admin")) {
            $("#admin-root", root).innerHTML = `
              <div class="center fade-in"><div class="card auth-card" style="text-align:center">
                <div class="status-icon err">${icon('<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>', 28)}</div>
                <h2>Admins only</h2><p class="sub">You need the <b>admin</b> role to manage users.</p>
                <a class="btn btn-primary" href="#/dashboard">Back to dashboard</a>
              </div></div>`;
            return;
          }
          let users = [];
          let query = "";
          const palette = ["#8b5cf6", "#06b6d4", "#ec4899", "#f59e0b", "#22c55e", "#3b82f6", "#ef4444"];
          const colorFor = (s) => palette[[...s].reduce((a, c) => a + c.charCodeAt(0), 0) % palette.length];

          $("#admin-root", root).innerHTML = `
            <div class="fade-in">
              <div class="page-head"><div><h1>User management</h1><p>Assign roles and deactivate accounts. Changes apply instantly.</p></div></div>
              <div class="stat-row" id="stats"></div>
              <section class="card" style="padding:24px">
                <div class="table-tools">
                  <div class="search input-wrap">${I.search.replace("<svg", '<svg class="lead"')}<input class="input" id="q" placeholder="Search by email…" /></div>
                  <button class="btn btn-ghost btn-sm" id="reload">${I.refresh}Reload</button>
                </div>
                <div class="table-wrap"><table>
                  <thead><tr><th>User</th><th>Status</th><th>Roles <span style="text-transform:none;letter-spacing:0;font-weight:400">(click to toggle)</span></th><th>Joined</th><th></th></tr></thead>
                  <tbody id="rows"></tbody>
                </table></div>
              </section>
            </div>`;

          const renderStats = () => {
            const s = (k, v, g) => `<div class="card stat"><div class="k">${k}</div><div class="v ${g ? "g" : ""}">${v}</div></div>`;
            $("#stats").innerHTML =
              s("Total users", users.length, true) +
              s("Active", users.filter((u) => u.is_active).length) +
              s("Verified", users.filter((u) => u.is_verified).length) +
              s("Admins", users.filter((u) => u.roles.includes("admin")).length);
          };

          const renderRows = () => {
            const list = users.filter((u) => u.email.toLowerCase().includes(query));
            $("#rows").innerHTML = list.length
              ? list.map((u) => `
                <tr class="${u.is_active ? "" : "inactive"}" data-id="${esc(u.id)}">
                  <td><div class="user-cell"><span class="mini-avatar" style="background:${colorFor(u.email)}">${esc(u.email[0].toUpperCase())}</span>
                    <div><div style="font-weight:600">${esc(u.email)}${u.id === me.id ? ' <span class="badge" style="margin-left:6px">you</span>' : ""}</div>
                    <div class="mono" style="color:var(--faint)">${esc(u.id.slice(0, 8))}…</div></div></div></td>
                  <td><div class="badges" style="margin:0">
                    ${u.is_active ? '<span class="badge ok">Active</span>' : '<span class="badge off">Deactivated</span>'}
                    ${u.is_verified ? '<span class="badge ok">Verified</span>' : '<span class="badge warn">Unverified</span>'}</div></td>
                  <td><div class="role-toggles">${ROLES.map((r) => `<span class="badge role-${r} role-toggle ${u.roles.includes(r) ? "on" : ""}" data-role="${r}">${r}</span>`).join("")}</div></td>
                  <td style="color:var(--muted);white-space:nowrap">${new Date(u.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}</td>
                  <td style="text-align:right">${u.is_active && u.id !== me.id ? `<button class="btn btn-danger btn-sm" data-deactivate>${I.trash}Deactivate</button>` : ""}</td>
                </tr>`).join("")
              : `<tr><td colspan="5" class="empty">No users match “${esc(query)}”.</td></tr>`;
          };

          const load = async () => {
            try {
              users = await request("/admin/users?limit=200", { auth: true });
            } catch (err) {
              return toast(err.message, "err");
            }
            renderStats();
            renderRows();
          };

          $("#q").addEventListener("input", (e) => { query = e.target.value.trim().toLowerCase(); renderRows(); });
          $("#reload").addEventListener("click", (e) => withBusy(e.currentTarget, load));
          $("#rows").addEventListener("click", async (e) => {
            const row = e.target.closest("tr[data-id]");
            if (!row) return;
            const user = users.find((u) => u.id === row.dataset.id);
            const toggle = e.target.closest("[data-role]");
            if (toggle) {
              const role = toggle.dataset.role;
              const roles = user.roles.includes(role) ? user.roles.filter((r) => r !== role) : [...user.roles, role];
              try {
                Object.assign(user, await request(`/admin/users/${user.id}/roles`, { method: "PUT", auth: true, body: { roles } }));
                toast(`Updated roles for ${user.email}`, "ok");
              } catch (err) {
                toast(err.message, "err");
              }
              renderStats();
              renderRows();
            }
            if (e.target.closest("[data-deactivate]")) {
              if (!confirm(`Deactivate ${user.email}? They will no longer be able to sign in.`)) return;
              try {
                await request(`/admin/users/${user.id}`, { method: "DELETE", auth: true });
                user.is_active = false;
                toast(`${user.email} deactivated`, "ok");
              } catch (err) {
                toast(err.message, "err");
              }
              renderStats();
              renderRows();
            }
          });
          await load();
        },
      };
    },
  };

  // ---------- Session helpers ----------
  async function loadUser() {
    try {
      state.user = await request("/auth/me", { auth: true });
      return state.user;
    } catch (err) {
      toast(err.message, "err");
      tokens.clear();
      state.user = null;
      go("login");
      return null;
    }
  }

  async function logout() {
    const t = tokens.get();
    tokens.clear();
    state.user = null;
    if (t?.refresh_token) {
      await request("/auth/logout", { method: "POST", body: { refresh_token: t.refresh_token } }).catch(() => {});
    }
    toast("Signed out", "info");
    go("login");
  }

  function startSessionTimer() {
    clearInterval(state.timer);
    const tick = async () => {
      const bar = $("#ring-bar");
      if (!bar) return clearInterval(state.timer);
      const t = tokens.get();
      if (!t) return;
      const p = decodeJwt(t.access_token);
      const total = p.exp && p.iat ? p.exp - p.iat : 900;
      const left = Math.max(0, Math.round((p.exp || 0) - Date.now() / 1000));
      $("#ring-time").textContent = `${String(Math.floor(left / 60)).padStart(2, "0")}:${String(left % 60).padStart(2, "0")}`;
      bar.style.strokeDashoffset = String(314.16 * (1 - left / total));
      const [h, pl, s] = t.access_token.split(".");
      $("#token-box").innerHTML = `<span class="h">${esc(h)}</span>.<span class="p">${esc(pl)}</span>.<span class="s">${esc(s)}</span>`;
      if (left <= 0) {
        clearInterval(state.timer);
        try {
          await refreshTokens();
          startSessionTimer();
        } catch {
          go("login");
        }
      }
    };
    tick();
    state.timer = setInterval(tick, 1000);
  }

  let health = null;
  async function checkHealth() {
    try {
      const res = await fetch(API_BASE + "/health");
      health = await res.json();
    } catch {
      health = { status: "unreachable", checks: {} };
    }
    const ok = health.status === "ok";
    $("#health").innerHTML = `<span class="pulse ${ok ? "ok" : "err"}"></span>${ok ? "All systems operational" : `Service ${esc(health.status)}`}`;
    renderHealthCard();
  }

  function renderHealthCard() {
    const box = $("#checks");
    if (!box || !health) return;
    const ok = health.status === "ok";
    $("#health-badge").className = `badge ${ok ? "ok" : "off"}`;
    $("#health-badge").textContent = ok ? `Healthy · v${health.version}` : health.status;
    const names = { database: "PostgreSQL / database", redis: "Redis cache" };
    box.innerHTML = Object.entries(health.checks || {})
      .map(([k, v]) => `<div class="check"><span class="left"><span class="pulse ${v === "ok" ? "ok" : "err"}"></span>${esc(names[k] || k)}</span><span class="badge ${v === "ok" ? "ok" : "off"}">${v === "ok" ? "Operational" : "Down"}</span></div>`)
      .join("") || `<div class="check">Health endpoint unreachable</div>`;
  }

  // ---------- Router ----------
  function parseHash() {
    const raw = location.hash.replace(/^#\/?/, "");
    const [path, qs = ""] = raw.split("?");
    return { route: path || (tokens.get() ? "dashboard" : "login"), params: new URLSearchParams(qs) };
  }

  function go(route) {
    if (location.hash === `#/${route}`) render();
    else location.hash = `#/${route}`;
  }

  function redirect(route) {
    setTimeout(() => go(route));
    return { html: "", mount() {} };
  }

  function render() {
    clearInterval(state.timer);
    let { route, params } = parseHash();
    if (!views[route]) route = "login";
    if ((route === "login" || route === "register") && tokens.get()) route = "dashboard";
    renderNav(route);
    const view = views[route](params);
    const root = $("#app");
    root.innerHTML = view.html;
    wireForm(root);
    Promise.resolve(view.mount(root)).catch((err) => toast(err.message, "err"));
    window.scrollTo(0, 0);
  }

  window.addEventListener("hashchange", render);
  render();
  checkHealth();
  setInterval(checkHealth, 30000);
})();
