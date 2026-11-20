// Runs in <head> before the page is drawn, so the visitor's display settings
// apply without a flash. Kept small and in its own file: the Content Security
// Policy does not allow inline scripts.
//   badeel-theme  light | dark              (default light)
//   badeel-text   sm | md | lg | xl | xxl   (default md)
//   badeel-view   simple | pro              (default set by the server for the role)
//   badeel-senior on | off
(function () {
  "use strict";
  var root = document.documentElement;
  root.classList.add("js");
  function read(key, allowed) {
    try {
      var v = window.localStorage.getItem(key);
      return allowed.indexOf(v) >= 0 ? v : null;
    } catch (e) { return null; }      // storage blocked: use the defaults
  }
  var theme = read("badeel-theme", ["light", "dark"]);
  var text = read("badeel-text", ["sm", "md", "lg", "xl", "xxl"]);
  var view = read("badeel-view", ["simple", "pro"]);
  var senior = read("badeel-senior", ["on", "off"]);
  root.setAttribute("data-theme", theme || "light");
  if (text) { root.setAttribute("data-text", text); }
  if (view) { root.setAttribute("data-view", view); }
  if (senior === "on") { root.setAttribute("data-senior", "on"); }
})();
