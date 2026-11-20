// Runs in <head> before the page is drawn, so the saved theme is applied
// without a flash. Kept tiny and in its own file: the Content Security
// Policy does not allow inline scripts.
(function () {
  "use strict";
  var root = document.documentElement;
  root.classList.add("js");
  try {
    var saved = window.localStorage.getItem("badeel-theme");
    if (saved === "light" || saved === "dark") { root.setAttribute("data-theme", saved); }
  } catch (e) { /* storage blocked: follow the system setting */ }
})();
