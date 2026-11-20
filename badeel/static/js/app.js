// Badeel front-end script. No libraries. The site works without it too;
// it only adds: display settings, closing menus, search suggestions and confirm dialogs.
(function () {
  "use strict";

  // ---- display settings: colours, text size, simple / clinical view, senior mode
  var root = document.documentElement;
  var SIZES = ["sm", "md", "lg", "xl", "xxl"];
  function save(key, value) { try { window.localStorage.setItem(key, value); } catch (e) { /* blocked */ } }
  function get(name, fallback) { return root.getAttribute(name) || fallback; }
  function set(name, value, key) { root.setAttribute(name, value); save(key, value); refresh(); }

  function refresh() {
    var senior = get("data-senior", "off") === "on";
    document.querySelectorAll("[data-set-theme]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-set-theme") === get("data-theme", "light")));
    });
    document.querySelectorAll("[data-set-view]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-set-view") === get("data-view", "simple")));
    });
    document.querySelectorAll("[data-senior-toggle]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(senior));
    });
    // in the clinical view, open the detail panels marked data-open-in-pro
    var pro = get("data-view", "simple") === "pro";
    document.querySelectorAll("details[data-open-in-pro]").forEach(function (d) { d.open = pro; });
  }

  document.addEventListener("click", function (event) {
    var b = event.target.closest("button");
    if (!b) { return; }
    if (b.hasAttribute("data-set-theme")) { set("data-theme", b.getAttribute("data-set-theme"), "badeel-theme"); }
    else if (b.hasAttribute("data-set-view")) { set("data-view", b.getAttribute("data-set-view"), "badeel-view"); }
    else if (b.hasAttribute("data-set-text")) { set("data-text", b.getAttribute("data-set-text"), "badeel-text"); }
    else if (b.hasAttribute("data-text-step")) {
      var i = SIZES.indexOf(get("data-text", "md"));
      var next = SIZES[Math.max(0, Math.min(SIZES.length - 1, i + Number(b.getAttribute("data-text-step"))))];
      set("data-text", next, "badeel-text");
    } else if (b.hasAttribute("data-senior-toggle")) {
      // senior mode = simple view + text 125%; turning it off goes back to the defaults
      if (get("data-senior", "off") === "on") {
        root.removeAttribute("data-senior"); save("badeel-senior", "off");
        set("data-text", "md", "badeel-text");
        set("data-view", root.getAttribute("data-default-view") || "simple", "badeel-view");
      } else {
        root.setAttribute("data-senior", "on"); save("badeel-senior", "on");
        set("data-text", "xl", "badeel-text");
        set("data-view", "simple", "badeel-view");
      }
    }
  });
  refresh();

  // ---- dropdown menus (<details>): close on outside click, Escape, or opening another
  var dropdowns = document.querySelectorAll("details.dropdown");
  dropdowns.forEach(function (d) {
    d.addEventListener("toggle", function () {
      if (!d.open) { return; }
      dropdowns.forEach(function (other) { if (other !== d) { other.open = false; } });
    });
  });
  document.addEventListener("click", function (event) {
    dropdowns.forEach(function (d) { if (d.open && !d.contains(event.target)) { d.open = false; } });
  });
  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") { return; }
    dropdowns.forEach(function (d) {
      if (d.open) { d.open = false; d.querySelector("summary").focus(); }
    });
  });

  // ---- "are you sure?" on dangerous forms (data-confirm="message")
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      var condition = form.getAttribute("data-confirm-if");   // e.g. "mode=replace"
      if (condition) {
        var parts = condition.split("=");
        var field = form.querySelector('[name="' + parts[0] + '"]:checked');
        if (!field || field.value !== parts[1]) { return; }
      }
      if (!window.confirm(form.getAttribute("data-confirm"))) { event.preventDefault(); }
    });
  });

  // ---- search suggestions
  var input = document.querySelector("input[data-suggest]");
  var list = document.getElementById("suggest");
  if (!input || !list) { return; }
  var timer = null, active = -1, lastQuery = "";

  function close() { list.hidden = true; list.innerHTML = ""; active = -1; }

  function render(items) {
    list.innerHTML = "";
    items.forEach(function (item) {
      var li = document.createElement("li");
      var a = document.createElement("a");
      a.href = item.url;
      // textContent (not innerHTML): drug names can never inject HTML.
      a.textContent = item.name + (item.name_ar ? "  " + item.name_ar : "");
      var small = document.createElement("small");
      small.textContent = item.detail;
      small.dir = "ltr";
      a.appendChild(small);
      li.appendChild(a);
      list.appendChild(li);
    });
    list.hidden = items.length === 0;
    active = -1;
  }

  input.addEventListener("input", function () {
    var q = input.value.trim();
    clearTimeout(timer);
    if (q.length < 2) { close(); return; }
    timer = setTimeout(function () {             // wait until typing pauses
      lastQuery = q;
      fetch(input.getAttribute("data-suggest") + "?q=" + encodeURIComponent(q))
        .then(function (r) { return r.ok ? r.json() : []; })
        .then(function (items) { if (q === lastQuery) { render(items); } })
        .catch(close);
    }, 180);
  });

  input.addEventListener("keydown", function (event) {
    var links = list.querySelectorAll("a");
    if (list.hidden || !links.length) { return; }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      active = (active + (event.key === "ArrowDown" ? 1 : -1) + links.length) % links.length;
      links.forEach(function (a, i) { a.classList.toggle("on", i === active); });
    } else if (event.key === "Enter" && active >= 0) {
      event.preventDefault();
      window.location.href = links[active].href;
    } else if (event.key === "Escape") {
      close();
    }
  });

  document.addEventListener("click", function (event) {
    if (!list.contains(event.target) && event.target !== input) { close(); }
  });
})();
