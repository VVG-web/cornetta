// Cornetta · sito statico. Nessuna analisi, nessun cookie, nessuna richiesta oltre alle risorse della pagina.
(function () {
  "use strict";
  var it = document.documentElement.lang !== "en";
  var labels = it
    ? { mac: "Scarica per Mac", win: "Scarica per Windows" }
    : { mac: "Download for Mac", win: "Download for Windows" };

  var isWindows = /Windows/i.test(navigator.userAgent);

  function showOS(windows) {
    document.querySelectorAll("[data-os]").forEach(function (el) {
      el.hidden = (el.getAttribute("data-os") === "windows") !== windows;
    });
    document.querySelectorAll("[data-download-primary]").forEach(function (a) {
      var span = a.querySelector("span");
      if (!a.hasAttribute("data-label-mac")) a.setAttribute("data-label-mac", span.textContent);
      span.textContent = windows ? labels.win : a.getAttribute("data-label-mac");
    });
  }

  if (isWindows) showOS(true);

  var nav = document.querySelector(".nav");
  if (nav) {
    var onScroll = function () { nav.classList.toggle("scrolled", window.scrollY > 8); };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }
})();
