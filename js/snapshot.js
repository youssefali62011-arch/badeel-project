// Static preview: there is no server behind these pages. Search forms open the
// sample results page; every other form only shows a short note.
(function () {
  "use strict";
  var note = document.createElement("div");
  note.className = "snap-note";
  note.setAttribute("role", "status");
  note.hidden = true;
  document.body.appendChild(note);
  var timer;
  function say(text) {
    note.textContent = text;
    note.hidden = false;
    clearTimeout(timer);
    timer = setTimeout(function () { note.hidden = true; }, 2600);
  }
  var ar = (document.documentElement.lang || document.querySelector("[lang]").lang) === "ar";
  document.addEventListener("submit", function (event) {
    var form = event.target;
    event.preventDefault();
    if (form.classList.contains("search")) { window.location.href = "search.html"; return; }
    say(ar ? "دي نسخة عرض ثابتة: الحفظ وتسجيل الدخول بيشتغلوا في الموقع الحقيقي بس."
           : "This is a static preview: saving and logging in work on the real site only.");
  }, true);
  document.addEventListener("click", function (event) {
    var a = event.target.closest("a[data-snap-off]");
    if (!a) { return; }
    event.preventDefault();
    say(ar ? "الصفحة دي مش موجودة في نسخة العرض." : "This page is not part of the preview.");
  });
})();
