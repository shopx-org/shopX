// static/js/banner_countdown.js

(() => {
  // 1) لاگ اینکه فایل چندبار اجرا شده
  window.__festivalCountdownLoaded = (window.__festivalCountdownLoaded || 0) + 1;
  console.log("banner_countdown.js loaded times =", window.__festivalCountdownLoaded);

  // 2) جلوی init چندباره (اگر اسکریپت دوبار لود شد)
  if (window.__festivalCountdownInit) {
    console.warn("festival countdown already initialized -> skip");
    return;
  }
  window.__festivalCountdownInit = true;

  // 3) بعد از آماده شدن DOM اجرا کن
  document.addEventListener("DOMContentLoaded", () => {
    const els = document.querySelectorAll("#festival-countdown");
    if (!els.length) {
      console.log("festival-countdown not found (no banner or countdown disabled)");
      return;
    }
    if (els.length > 1) {
      console.warn("Duplicate #festival-countdown ids found:", els.length, "(HTML bug) -> using first one");
    }

    const el = els[0];

    // 4) اگر قبلاً تایمر روی همین عنصر ست شده، پاکش کن (پیشگیری از تداخل)
    if (el.__timerId) {
      clearInterval(el.__timerId);
      el.__timerId = null;
    }

    // 5) دریافت end time از data-end-ms یا fallback از data-end
    const endMsAttr = (el.getAttribute("data-end-ms") || "").trim();
    const endIsoAttr = (el.getAttribute("data-end") || "").trim();

    let end = Number.NaN;

    if (endMsAttr) {
      end = Number.parseInt(endMsAttr, 10);
    } else if (endIsoAttr) {
      end = Date.parse(endIsoAttr);
    }

    if (!Number.isFinite(end) || Number.isNaN(end)) {
      console.warn("Countdown end is invalid.", {
        dataEndMs: endMsAttr,
        dataEndIso: endIsoAttr,
      });
      return;
    }

    // 6) نودهای نمایش
    const nodes = {
      d: el.querySelector('[data-k="d"]'),
      h: el.querySelector('[data-k="h"]'),
      m: el.querySelector('[data-k="m"]'),
      s: el.querySelector('[data-k="s"]'),
    };

    const pad2 = (n) => String(n).padStart(2, "0");
    const toFaDigits = (str) => String(str).replace(/\d/g, (d) => "۰۱۲۳۴۵۶۷۸۹"[d]);

    function tick() {
      const now = Date.now();
      let diff = Math.max(0, end - now);

      const d = Math.floor(diff / 86400000);
      diff -= d * 86400000;

      const h = Math.floor(diff / 3600000);
      diff -= h * 3600000;

      const m = Math.floor(diff / 60000);
      diff -= m * 60000;

      const s = Math.floor(diff / 1000);

      if (nodes.d) nodes.d.textContent = toFaDigits(d);
      if (nodes.h) nodes.h.textContent = toFaDigits(pad2(h));
      if (nodes.m) nodes.m.textContent = toFaDigits(pad2(m));
      if (nodes.s) nodes.s.textContent = toFaDigits(pad2(s));

      // وقتی تموم شد، تایمر رو قطع کن
      if (end - now <= 0) {
        clearInterval(el.__timerId);
        el.__timerId = null;
        console.log("countdown finished ✅");
        // اگر خواستی اینجا رفرش کنی:
        // location.reload();
      }
    }

    // 7) شروع
    console.log("countdown init ✅", {
      endMs: end,
      endIso: new Date(end).toISOString(),
      nowIso: new Date().toISOString(),
      dataEndMs: endMsAttr,
      dataEndIso: endIsoAttr,
    });

    tick();
    el.__timerId = setInterval(tick, 1000);
  });
})();














// cconsole.log("banner_countdown loaded ✅");
//
// (function () {
//   const el = document.getElementById("festival-countdown");
//   if (!el) return;
//
//   const endMsAttr = el.getAttribute("data-end-ms");
//   const end = parseInt(endMsAttr, 10);
//   if (!Number.isFinite(end)) {
//     console.warn("Invalid data-end-ms:", endMsAttr);
//     return;
//   }
//
//   const nodes = {
//     d: el.querySelector('[data-k="d"]'),
//     h: el.querySelector('[data-k="h"]'),
//     m: el.querySelector('[data-k="m"]'),
//     s: el.querySelector('[data-k="s"]'),
//   };
//
//   const pad2 = (n) => String(n).padStart(2, "0");
//   const toFaDigits = (str) => String(str).replace(/\d/g, d => "۰۱۲۳۴۵۶۷۸۹"[d]);
//
//   function tick() {
//     const now = Date.now();
//     let diff = Math.max(0, end - now);
//
//     const d = Math.floor(diff / (24 * 3600 * 1000));
//     diff -= d * 24 * 3600 * 1000;
//
//     const h = Math.floor(diff / (3600 * 1000));
//     diff -= h * 3600 * 1000;
//
//     const m = Math.floor(diff / (60 * 1000));
//     diff -= m * 60 * 1000;
//
//     const s = Math.floor(diff / 1000);
//
//     if (nodes.d) nodes.d.textContent = toFaDigits(d);
//     if (nodes.h) nodes.h.textContent = toFaDigits(pad2(h));
//     if (nodes.m) nodes.m.textContent = toFaDigits(pad2(m));
//     if (nodes.s) nodes.s.textContent = toFaDigits(pad2(s));
//
//     if (end - now <= 0) {
//       // اگر می‌خوای بعد از اتمام، بنر/صفحه رفرش شه:
//       // location.reload();
//       clearInterval(timer);
//     }
//   }
//
//   tick();
//   const timer = setInterval(tick, 1000);
// })();