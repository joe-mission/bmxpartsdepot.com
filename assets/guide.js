/* ============================================================
   BMX PARTS DEPOT - guide pages
   Progressive enhancement only. Every page is fully readable
   with this file blocked or failed. Nothing here creates content.
   ============================================================ */
(function () {
  "use strict";

  /* ---------- hub: live filter over the guides and the A-Z ---------- */
  var search = document.getElementById("dict-search");
  var results = document.getElementById("az-results");
  var empty = document.getElementById("no-results");
  var count = document.getElementById("search-count");
  var grid = document.getElementById("pillar-grid");
  var guidesHead = document.getElementById("guides-head");
  var guidesRule = document.getElementById("guides-rule");

  if (search && results) {
    var groups = Array.prototype.slice.call(results.querySelectorAll(".az-group"));
    var cards = grid ? Array.prototype.slice.call(grid.querySelectorAll(".pillar-card")) : [];
    var timer = null;

    var filter = function () {
      var q = search.value.trim().toLowerCase();
      var shown = 0;
      var cardHits = 0;

      /* guides first: they are what most people are actually after, and
         they sit above the fold, so filtering them is what makes typing
         look like it did something */
      cards.forEach(function (c) {
        var hay = c.getAttribute("data-term") || c.textContent.toLowerCase();
        var match = !q || hay.indexOf(q) !== -1;
        c.hidden = !match;
        if (match) cardHits++;
      });
      if (guidesHead) guidesHead.hidden = q !== "" && cardHits === 0;
      if (guidesRule) guidesRule.hidden = q !== "" && cardHits === 0;

      groups.forEach(function (g) {
        var hits = 0;
        var items = g.querySelectorAll("li");
        Array.prototype.forEach.call(items, function (li) {
          var a = li.querySelector("a");
          var hay = (a && a.getAttribute("data-term")) || li.textContent.toLowerCase();
          var match = !q || hay.indexOf(q) !== -1;
          li.hidden = !match;
          if (match) hits++;
        });
        g.hidden = hits === 0;
        shown += hits;
      });

      if (empty) empty.hidden = shown !== 0 || cardHits !== 0;

      /* the results live well below the fold, so say what happened up
         here at the box rather than leaving it looking inert */
      if (count) {
        if (!q) {
          count.hidden = true;
          count.textContent = "";
        } else {
          count.hidden = false;
          var bits = [];
          if (cardHits) bits.push(cardHits + (cardHits === 1 ? " guide" : " guides"));
          if (shown) bits.push(shown + (shown === 1 ? " term" : " terms"));
          count.textContent = bits.length
            ? bits.join(" and ") + " match “" + search.value.trim() + "”"
            : "Nothing matches “" + search.value.trim() + "”";
          count.className = "search-count" + (bits.length ? "" : " none");
        }
      }
    };

    search.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(filter, 90);
    });

    /* Enter on a single result goes straight there */
    search.addEventListener("keydown", function (e) {
      if (e.key !== "Enter") return;
      var visible = results.querySelectorAll(".az-group:not([hidden]) li:not([hidden]) a");
      if (visible.length === 1) {
        e.preventDefault();
        window.location.href = visible[0].getAttribute("href");
      }
    });
  }

  /* ---------- hub: A-Z jump bar ---------- */
  var bar = document.querySelector(".az-bar");
  if (bar && results) {
    bar.addEventListener("click", function (e) {
      var btn = e.target.closest("button[data-jump]");
      if (!btn) return;
      var letter = btn.getAttribute("data-jump");
      var target = document.getElementById("letter-" + letter);
      if (!target) return;

      /* clear any active filter first, otherwise the jump lands nowhere */
      if (search && search.value) {
        search.value = "";
        search.dispatchEvent(new Event("input"));
      }
      setTimeout(function () {
        target.scrollIntoView({ block: "start", behavior: prefersReduced() ? "auto" : "smooth" });
      }, 0);
    });
  }

  /* ---------- guide pages: table of contents scrollspy ---------- */
  var toc = document.querySelector(".toc");
  if (toc && "IntersectionObserver" in window) {
    var links = {};
    Array.prototype.forEach.call(toc.querySelectorAll("a[href^='#']"), function (a) {
      links[a.getAttribute("href").slice(1)] = a;
    });

    var headings = Object.keys(links)
      .map(function (id) { return document.getElementById(id); })
      .filter(Boolean);

    if (headings.length) {
      var current = null;
      var io = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (!entry.isIntersecting) return;
            var a = links[entry.target.id];
            if (!a || a === current) return;
            if (current) current.classList.remove("active");
            a.classList.add("active");
            current = a;
          });
        },
        { rootMargin: "-88px 0px -70% 0px", threshold: 0 }
      );
      headings.forEach(function (h) { io.observe(h); });
    }
  }

  function prefersReduced() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }
})();

/* ---- mobile menu ----------------------------------------------------
   Mirrors the homepage script. The panel is [hidden] in the markup, so
   with JS off it stays closed rather than leaving a dead toggle. */
(function () {
  var btn = document.getElementById('navToggle');
  var panel = document.getElementById('navPanel');
  var scrim = document.getElementById('navScrim');
  if (!btn || !panel) return;

  function setOpen(open) {
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    btn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    panel.hidden = !open;
    if (scrim) scrim.classList.toggle('is-open', open);
  }

  btn.addEventListener('click', function (e) {
    e.stopPropagation();
    setOpen(panel.hidden);
  });
  panel.addEventListener('click', function (e) {
    if (e.target.closest('a')) setOpen(false);
  });
  document.addEventListener('click', function (e) {
    if (!panel.hidden && !panel.contains(e.target) && e.target !== btn) setOpen(false);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !panel.hidden) { setOpen(false); btn.focus(); }
  });
  window.addEventListener('resize', function () {
    if (window.innerWidth > 900 && !panel.hidden) setOpen(false);
  }, { passive: true });
})();

/* ---- hub: search toggle -------------------------------------------
   The input starts collapsed behind a magnifier at the end of the A-Z
   row and slides out over the letters. Its own IIFE so it cannot be
   taken out by anything above it. Filtering itself is untouched: this
   only opens, closes and clears. */
(function () {
  var row = document.getElementById("azRow");
  var btn = document.getElementById("searchToggle");
  var input = document.getElementById("dict-search");
  if (!row || !btn || !input) return;

  function setOpen(open) {
    row.classList.toggle("is-open", open);
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    btn.setAttribute("aria-label", open ? "Close search" : "Search the guide");
    /* Collapsed the input is 0 wide and must stay out of the tab order,
       or keyboard users land in a field they cannot see. */
    input.setAttribute("tabindex", open ? "0" : "-1");
    if (open) {
      input.focus();
    } else if (input.value) {
      /* Closing with a query left behind would leave the page filtered
         with no visible reason. Clear it, and fire the event the filter
         above listens for so the full list comes back. */
      input.value = "";
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }
  }

  btn.addEventListener("click", function (e) {
    e.stopPropagation();
    setOpen(!row.classList.contains("is-open"));
  });

  input.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { setOpen(false); btn.focus(); }
  });

  /* Click away closes, but only when nothing has been typed, so a stray
     click does not throw away a query mid-search. */
  document.addEventListener("click", function (e) {
    if (!row.classList.contains("is-open")) return;
    if (row.contains(e.target)) return;
    if (!input.value) setOpen(false);
  });
})();
