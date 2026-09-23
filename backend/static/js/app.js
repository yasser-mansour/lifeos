// LIFEOS shared client behavior: theme, command palette, drawers/modals, toasts.
// No framework, no build step — vanilla JS kept deliberately small.

(function () {
  "use strict";

  /* ---------------- Theme ---------------- */
  const ThemeManager = {
    KEY: "lifeos-theme",
    init() {
      const saved = localStorage.getItem(this.KEY);
      if (saved === "light" || saved === "dark") {
        document.documentElement.setAttribute("data-theme", saved);
      }
    },
    set(theme) {
      if (theme === "system") {
        document.documentElement.removeAttribute("data-theme");
        localStorage.removeItem(this.KEY);
      } else {
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem(this.KEY, theme);
      }
    },
  };
  ThemeManager.init();
  window.LifeOS = window.LifeOS || {};
  window.LifeOS.ThemeManager = ThemeManager;

  /* ---------------- CSRF-aware fetch ---------------- */
  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
    return match ? decodeURIComponent(match[2]) : null;
  }

  function apiFetch(url, options = {}) {
    const opts = Object.assign({ headers: {} }, options);
    opts.headers = Object.assign(
      {
        "X-CSRFToken": getCookie("csrftoken"),
        "X-Requested-With": "XMLHttpRequest",
      },
      options.headers || {}
    );
    if (opts.body && !(opts.body instanceof FormData) && typeof opts.body !== "string") {
      opts.body = JSON.stringify(opts.body);
      opts.headers["Content-Type"] = "application/json";
    }
    return fetch(url, opts);
  }
  window.LifeOS.apiFetch = apiFetch;

  /* ---------------- Toasts ---------------- */
  function ensureToastStack() {
    let stack = document.querySelector(".toast-stack");
    if (!stack) {
      stack = document.createElement("div");
      stack.className = "toast-stack";
      document.body.appendChild(stack);
    }
    return stack;
  }

  function toast(message, kind = "default") {
    const stack = ensureToastStack();
    const el = document.createElement("div");
    el.className = `toast ${kind}`;
    el.innerHTML = `<span class="dot dot-accent"></span><span>${message}</span>`;
    stack.appendChild(el);
    setTimeout(() => {
      el.style.transition = "opacity 180ms ease";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 200);
    }, 2600);
  }
  window.LifeOS.toast = toast;

  /* ---------------- Generic open/close (drawers, modals, palette) ---------------- */
  function bindOverlay(triggerSelector, targetId) {
    document.querySelectorAll(triggerSelector).forEach((trigger) => {
      trigger.addEventListener("click", () => openOverlay(targetId));
    });
  }

  function openOverlay(targetId) {
    const el = document.getElementById(targetId);
    if (!el) return;
    el.classList.add("open");
    const focusable = el.querySelector("input, textarea, select, [tabindex]");
    if (focusable) setTimeout(() => focusable.focus(), 50);
    document.body.classList.add("overlay-open");
  }

  function closeOverlay(targetId) {
    const el = typeof targetId === "string" ? document.getElementById(targetId) : targetId;
    if (!el) return;
    el.classList.remove("open");
    document.body.classList.remove("overlay-open");
  }

  function closeAllOverlays() {
    document.querySelectorAll(".open").forEach((el) => el.classList.remove("open"));
    document.body.classList.remove("overlay-open");
  }

  window.LifeOS.openOverlay = openOverlay;
  window.LifeOS.closeOverlay = closeOverlay;

  document.addEventListener("click", (e) => {
    const closeTarget = e.target.closest("[data-close-overlay]");
    if (closeTarget) {
      closeOverlay(closeTarget.getAttribute("data-close-overlay") || closeTarget.closest(".drawer, .modal-backdrop, .palette-backdrop"));
    }
    if (e.target.classList.contains("drawer-backdrop") || e.target.classList.contains("modal-backdrop") || e.target.classList.contains("palette-backdrop")) {
      closeOverlay(e.target);
    }
    const openTarget = e.target.closest("[data-open-overlay]");
    if (openTarget) {
      openOverlay(openTarget.getAttribute("data-open-overlay"));
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeAllOverlays();
  });

  /* ---------------- Back navigation ----------------
   * data-back-link's href is always a real, server-rendered fallback URL
   * (e.g. an account's own context page) — that alone satisfies "never
   * dead-ends." When we can tell the previous history entry is actually
   * another LIFEOS page (same-origin referrer), history.back() is used
   * instead so filters/tab/scroll position come back for free instead of
   * reconstructing them — see DESIGN_SYSTEM_V2.md "Back navigation." */
  document.addEventListener("click", (e) => {
    const backLink = e.target.closest("[data-back-link]");
    if (!backLink) return;
    const cameFromLifeos = document.referrer && document.referrer.startsWith(window.location.origin);
    if (cameFromLifeos && window.history.length > 1) {
      e.preventDefault();
      window.history.back();
    }
    // else: let the normal navigation to the href fallback proceed.
  });

  /* ---------------- Generic fetch-into-drawer (task/person/session detail) ---------------- */
  function loadDrawer(url) {
    const drawer = document.getElementById("detail-drawer");
    if (!drawer) return;
    const body = drawer.querySelector(".drawer-body");
    body.innerHTML = '<div class="stack"><div class="skeleton" style="height:22px;width:55%;"></div><div class="skeleton" style="height:14px;width:80%;"></div><div class="skeleton" style="height:14px;width:65%;"></div></div>';
    openOverlay("detail-drawer");
    apiFetch(url)
      .then((r) => r.text())
      .then((html) => {
        body.innerHTML = html;
      })
      .catch(() => {
        body.innerHTML = '<div class="empty-state"><div class="empty-state-body">Couldn\'t load this item.</div></div>';
      });
  }
  window.LifeOS.loadDrawer = loadDrawer;

  document.addEventListener("click", (e) => {
    const trigger = e.target.closest("[data-drawer-url]");
    if (trigger) {
      e.preventDefault();
      loadDrawer(trigger.getAttribute("data-drawer-url"));
    }
  });

  // Forms rendered inside the drawer submit via fetch; on success we reload
  // so list rows (counts, statuses) stay in sync with what just changed.
  document.addEventListener("submit", (e) => {
    const form = e.target.closest(".drawer-form");
    if (!form) return;
    e.preventDefault();
    apiFetch(form.action, { method: form.method || "POST", body: new FormData(form) }).then(() => {
      window.location.reload();
    });
  });

  /* ---------------- Sidebar collapse (desktop) ---------------- */
  document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.querySelector("[data-sidebar-toggle]");
    const sidebar = document.querySelector(".sidebar");
    if (toggle && sidebar) {
      const collapsed = localStorage.getItem("lifeos-sidebar-collapsed") === "1";
      if (collapsed) sidebar.classList.add("collapsed");
      toggle.addEventListener("click", () => {
        sidebar.classList.toggle("collapsed");
        localStorage.setItem("lifeos-sidebar-collapsed", sidebar.classList.contains("collapsed") ? "1" : "0");
      });
    }
  });

  /* ---------------- Sidebar open/close (narrow window) ---------------- */
  document.addEventListener("DOMContentLoaded", () => {
    const sidebar = document.querySelector(".sidebar");
    if (!sidebar) return;
    const mobileToggle = document.querySelector("[data-toggle-sidebar]");
    const closeMobileSidebar = () => sidebar.classList.remove("mobile-open");
    if (mobileToggle) {
      mobileToggle.addEventListener("click", () => sidebar.classList.toggle("mobile-open"));
    }
    document.querySelectorAll("[data-close-sidebar]").forEach((el) => el.addEventListener("click", closeMobileSidebar));
    sidebar.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeMobileSidebar));
  });

  /* ---------------- Command palette ---------------- */
  const Palette = {
    el: null,
    input: null,
    results: null,
    items: [],
    activeIndex: 0,
    debounceTimer: null,

    init() {
      this.el = document.getElementById("command-palette");
      if (!this.el) return;
      this.input = this.el.querySelector(".palette-input");
      this.results = this.el.querySelector(".palette-results");

      document.addEventListener("keydown", (e) => {
        const metaK = (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k";
        if (metaK) {
          e.preventDefault();
          this.open();
        }
      });

      this.input.addEventListener("input", () => {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => this.search(this.input.value), 140);
      });

      this.input.addEventListener("keydown", (e) => {
        const rows = Array.from(this.results.querySelectorAll(".palette-item"));
        if (e.key === "ArrowDown") {
          e.preventDefault();
          this.move(rows, 1);
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          this.move(rows, -1);
        } else if (e.key === "Enter") {
          e.preventDefault();
          const active = rows[this.activeIndex];
          if (active) active.click();
        }
      });
    },

    open() {
      openOverlay("command-palette");
      this.input.value = "";
      this.search("");
    },

    move(rows, delta) {
      if (!rows.length) return;
      rows[this.activeIndex] && rows[this.activeIndex].classList.remove("active");
      this.activeIndex = (this.activeIndex + delta + rows.length) % rows.length;
      rows[this.activeIndex].classList.add("active");
      rows[this.activeIndex].scrollIntoView({ block: "nearest" });
    },

    search(query) {
      this.activeIndex = 0;
      apiFetch(`/search/api/?q=${encodeURIComponent(query)}`)
        .then((r) => r.json())
        .then((data) => this.render(data))
        .catch(() => this.render({ groups: [] }));
    },

    render(data) {
      const groups = data.groups || [];
      if (!groups.length) {
        this.results.innerHTML = '<div class="empty-state" style="padding:32px 16px;"><div class="empty-state-body">No results. Try a different search, or use an action below.</div></div>';
        return;
      }
      this.results.innerHTML = groups
        .map(
          (g) => `
        <div class="palette-group-label">${g.label}</div>
        ${g.items
          .map(
            (item, i) => `
          <a class="palette-item${i === 0 && g === groups[0] ? " active" : ""}" href="${item.url}">
            ${item.icon_svg || ""}
            <span>${item.title}</span>
            ${item.hint ? `<span class="palette-item-hint">${item.hint}</span>` : ""}
          </a>`
          )
          .join("")}
      `
        )
        .join("");
    },
  };

  document.addEventListener("DOMContentLoaded", () => Palette.init());
  window.LifeOS.Palette = Palette;

  /* ---------------- Autosave helper (Journal / Writing) ---------------- */
  window.LifeOS.autosave = function (form, statusEl, url) {
    let timer = null;
    const save = () => {
      const data = new FormData(form);
      statusEl.textContent = "Saving…";
      apiFetch(url, { method: "POST", body: data })
        .then((r) => r.json())
        .then(() => {
          statusEl.textContent = "Saved";
        })
        .catch(() => {
          statusEl.textContent = "Couldn't save — will retry";
          timer = setTimeout(save, 4000);
        });
    };
    form.addEventListener("input", () => {
      statusEl.textContent = "Editing…";
      clearTimeout(timer);
      timer = setTimeout(save, 900);
    });
  };

  /* ---------------- Activity heartbeat (auto-lock) ---------------- */
  // AutoLockMiddleware refreshes last-activity on every real request, but a
  // long stretch of typing (Journal/Writing) or reading with no navigation
  // and no autosave in flight would otherwise look idle. Ping on genuine
  // interaction only — never on a timer — throttled so it costs at most one
  // request a minute, matching the "mouse/keyboard/nav/interaction, not
  // background timers" definition of activity.
  (function () {
    let lastPing = 0;
    const THROTTLE_MS = 60000;
    function ping() {
      const now = Date.now();
      if (now - lastPing < THROTTLE_MS) return;
      lastPing = now;
      apiFetch("/activity/ping/", { method: "POST" }).catch(() => {});
    }
    ["mousedown", "keydown", "scroll", "touchstart"].forEach((evt) => {
      document.addEventListener(evt, ping, { passive: true });
    });
  })();
})();
