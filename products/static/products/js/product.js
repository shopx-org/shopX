

/* ======================= PRODUCT: Variant resolution + live pricing + form wiring ======================= */
(function () {
  'use strict';

  // ---------- Shorthands ----------
  const $  = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  // ---------- Elements ----------
  const form         = $("#add-to-cart-form");
  const hiddenVid    = $("#variant_id");
  const btnAdd       = $("#btn-add");
  const qtyInput     = $("#qty");
  const colorWrap    = $("#color-swatches");
  const sizeSelect   = $("#size");
  const mainImg      = $("#tlp-main");

  // قیمت/تخفیف UI
  const elPriceNum   = $("#price-num");
  const elCompareNum = $("#compare-num");
  const elSaveBox    = $("#price-save");
  const elOffBadge   = $("#off-badge");
  const elOffAmount  = $("#off-amount");
  const lowStockEl   = $(".low-stock");

  // ---------- Data from template (JSON tags) ----------
  // variant-matrix: { matrix: { "<color_id>": { "<size_id|OS>": { price, stock, sku, compare_at?, variant_id? } } , sizes: {...}} }
  // variant-prices: { "<variant_id>": { price, stock, sku, compare_at? } }
  function readJSON(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    try { return JSON.parse(el.textContent || el.innerText || 'null'); } catch { return null; }
  }
  const matrixObj = readJSON('variant-matrix') || {};
  const vprices   = readJSON('variant-prices') || {};
  const M         = matrixObj.matrix || {};
  const SIZES_META= matrixObj.sizes  || {};

  // optional API endpoint (for precise pricing after optimistic update)
  const priceApi  = $("#price-api")?.dataset?.url || null;

  // ---------- Helpers ----------
  const intcomma  = (n) => (Number.isFinite(n) ? n.toLocaleString("fa-IR") : "");
  const clamp     = (x, a, b) => Math.min(Math.max(x, a), b);

  function isSizeRequired(colorId) {
    const row = M[String(colorId)] || {};
    const keys = Object.keys(row || {});
    if (!keys.length) return false;
    // اگر کلید «OS» تنها گزینه نباشد، سایز اجباری است
    return !(keys.length === 1 && keys[0] === "OS");
  }

  function resolveVariantCell(colorId, sizeId) {
    if (!colorId) return null;
    const row = M[String(colorId)] || {};
    // اگر سایز انتخاب نشده، تلاش کن از OS یا اولین کلید پر شود
    let key = sizeId || (row["OS"] ? "OS" : Object.keys(row)[0]);
    if (!key) return null;
    return row[String(key)] || null;
  }

  function resolveVariantId(colorId, sizeId) {
    const cell = resolveVariantCell(colorId, sizeId);
    if (!cell) return null;
    // ترجیح با variant_id در ماتریس؛ در غیر این صورت اگر فقط یک کلید در vprices با sku match شد.
    if (cell.variant_id) return String(cell.variant_id);

    // fallback: اگر cell.sku داریم و در vprices دقیقاً یک واریانت با همان sku یافت شد
    if (cell.sku) {
      const matches = Object.entries(vprices).filter(([, v]) => (v && v.sku) === cell.sku);
      if (matches.length === 1) return String(matches[0][0]);
    }
    return null;
  }

  function setPriceUI({ finalPrice, basePrice, discountPercent, discountAmount }) {
    if (elPriceNum) elPriceNum.textContent = intcomma(finalPrice || 0);

    const hasDiscount = !!(basePrice && finalPrice && finalPrice < basePrice);
    if (!elSaveBox || !elCompareNum || !elOffBadge || !elOffAmount) return;

    if (hasDiscount) {
      elCompareNum.textContent = intcomma(basePrice);
      elOffBadge.textContent   = `${Math.round(discountPercent || 0)}٪ تخفیف`;
      elOffAmount.textContent  = discountAmount
        ? `مبلغ کسرشده: ${intcomma(discountAmount)} تومان`
        : "";
      elSaveBox.style.display  = "";
    } else {
      elSaveBox.style.display  = "none";
      elCompareNum.textContent = "";
      elOffBadge.textContent   = "";
      elOffAmount.textContent  = "";
    }
  }

  function optimisticUpdate(variantId, cell) {
    // اولویت با vprices؛ اگر نبود از cell استفاده کن
    const cached = vprices[String(variantId)] || cell || {};
    const finalPrice = Number(cached.price ?? 0);
    const basePrice  = Number(cached.compare_at ?? 0);
    const hasDisc    = basePrice && finalPrice && finalPrice < basePrice;
    const discountAmount  = hasDisc ? (basePrice - finalPrice) : 0;
    const discountPercent = hasDisc ? ((discountAmount / basePrice) * 100) : 0;

    setPriceUI({
      finalPrice,
      basePrice: hasDisc ? basePrice : null,
      discountPercent: hasDisc ? discountPercent : null,
      discountAmount: hasDisc ? discountAmount : null
    });
  }

  async function fetchAndFix(variantId) {
    if (!priceApi || !variantId) return;
    try {
      const url = new URL(priceApi, window.location.origin);
      url.searchParams.set("variant", String(variantId));
      const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      if (!res.ok) return;
      const data = await res.json();
      if (!data || data.ok === false) return;

      setPriceUI({
        finalPrice: Number(data.price_final ?? 0),
        basePrice:  (data.price_base ?? null),
        discountPercent: (data.discount_percent ?? null),
        discountAmount:  (data.discount_amount  ?? null)
      });
    } catch (_e) {
      // سکوت: optimistic کفایت می‌کند
    }
  }

  function updateLowStock(stock) {
    if (!lowStockEl) return;
    if (stock > 0 && stock <= 5) {
      lowStockEl.style.display = '';
      lowStockEl.textContent = 'تنها ' + intcomma(stock) + ' عدد در انبار باقی مانده';
    } else {
      lowStockEl.style.display = 'none';
    }
  }

  function enableAdd(enabled) {
    if (!btnAdd) return;
    btnAdd.disabled = !enabled;
    btnAdd.classList.toggle('is-disabled', !enabled);
    btnAdd.setAttribute('aria-disabled', (!enabled).toString());
  }

  function swapImageForColor(colorId) {
    if (!colorId || !mainImg) return;
    const btn = document.querySelector(`.thumb[data-color-id="${colorId}"]`);
    const src = btn?.dataset?.full || null;
    if (src) mainImg.setAttribute("src", src);
    $$(".thumb").forEach(b => b.classList.toggle("is-active", b === btn));
  }

  // ---------- State ----------
  let selectedColorId = (colorWrap?.querySelector(".active")?.dataset?.colorId) || null;
  let selectedSizeId  = (sizeSelect && sizeSelect.value && sizeSelect.value !== "#") ? sizeSelect.value : null;

  // ---------- Main selection handler ----------
  async function onSelectionChange() {
    // اگر رنگی انتخاب نشده، اولین رنگ موجود را انتخابِ منطقی کن
    if (!selectedColorId) {
      const first = colorWrap?.querySelector('a[data-color-id]')?.getAttribute('data-color-id');
      if (first) selectedColorId = first;
    }

    // اگر سایز لازم است ولی انتخاب نشده، فعلاً دکمه را غیرفعال کن
    if (selectedColorId && isSizeRequired(selectedColorId) && !selectedSizeId) {
      enableAdd(false);
      if (hiddenVid) hiddenVid.value = "";
      return;
    }

    // رزولوشن واریانت
    const cell = resolveVariantCell(selectedColorId, selectedSizeId);
    const variantId = resolveVariantId(selectedColorId, selectedSizeId);

    // ست کردن hidden
    if (hiddenVid) hiddenVid.value = variantId ? String(variantId) : "";

    // تصویر متناسب رنگ
    if (selectedColorId) swapImageForColor(selectedColorId);

    // کنترل موجودی و فعال/غیرفعال کردن دکمه
    const stock = Number(cell?.stock ?? vprices[variantId]?.stock ?? 0);
    updateLowStock(stock);
    enableAdd(!!(variantId && stock > 0));

    // قیمت: optimistic و سپس دقیق از API
    if (variantId) {
      optimisticUpdate(variantId, cell);
      fetchAndFix(variantId);
    }
  }

  // ---------- Events ----------
  // رنگ
  if (colorWrap) {
    $$("#color-swatches a[data-color-id]").forEach(a => {
      // انتقال color-id به dataset برای اطمینان
      if (!a.dataset.colorId) a.dataset.colorId = a.getAttribute("data-color-id") || "";
      a.addEventListener("click", (ev) => {
        ev.preventDefault();
        $$("#color-swatches a").forEach(x => x.classList.remove("active"));
        a.classList.add("active");
        selectedColorId = a.dataset.colorId || null;
        // اگر سایز OS تنها گزینه است، سایز را null نگه می‌داریم
        if (!isSizeRequired(selectedColorId)) selectedSizeId = null;
        onSelectionChange();
      });
    });
  }

  // سایز
  if (sizeSelect) {
    sizeSelect.addEventListener("change", () => {
      const v = sizeSelect.value;
      selectedSizeId = (v && v !== "#") ? v : null;
      onSelectionChange();
    });
  }

  // اعتبارسنجی نهایی فرم قبل از ارسال
  if (form) {
    form.addEventListener("submit", (e) => {
      // تعداد
      if (qtyInput) {
        const min = Number(qtyInput.min || 1);
        const max = Number(qtyInput.max || 99);
        qtyInput.value = String(clamp(Number(qtyInput.value || 1), min, max));
      }

      // واریانت
      const vid = hiddenVid?.value || "";
      const sizeNeeded = selectedColorId && isSizeRequired(selectedColorId);
      if (!vid || (sizeNeeded && !selectedSizeId)) {
        e.preventDefault();
        // پیام ساده؛ اگر سیستم نوتیفیکیشن داری، اینجا جایگزین کن
        alert(sizeNeeded && !selectedSizeId ? "لطفاً سایز را انتخاب کنید." : "لطفاً یک واریانت معتبر انتخاب کنید.");
        enableAdd(false);
        return false;
      }
    });
  }

  // ---------- Initial run ----------
  onSelectionChange();

})();
(function () {
  // فقط بعد از آماده‌شدن DOM اجرا شود
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }

  function cssVar(name, fallback) {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name);
    return (v && v.trim()) || fallback;
  }

  function faNum(n) {
    return Number(n ?? 0).toLocaleString("fa-IR");
  }

  function boot() {
    // 1) وجود عنصر و خود Chart.js را چک کن
    const el = document.getElementById("priceLineChart");
    if (!el || typeof window.Chart === "undefined") return;

    // 2) گرفتن context به‌صورت امن
    const ctx = el.getContext && el.getContext("2d");
    if (!ctx) return;

    // 3) امکان تزریق داده از data-* روی canvas
    //   <canvas id="priceLineChart" data-labels='["فروردین",...]' data-points='[12,42,...]'></canvas>
    let labels =
      tryJSON(el.dataset.labels) ??
      ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور","مهر","آبان","آذر"];

    let dataPoints =
      tryJSON(el.dataset.points) ?? [12, 42, 36, 50, 49, 61, 68, 92, 150];

    // هم‌طول‌کردنِ labels و data
    const len = Math.min(labels.length, dataPoints.length);
    labels = labels.slice(0, len);
    dataPoints = dataPoints.slice(0, len);

    // 4) رنگ‌ها از CSS Variables با fallback
    const lineColor = cssVar("--line", "#6c8cff");
    const gridColor = cssVar("--grid", "#eff3f8");
    const ticksColor = cssVar("--axis-muted", "#9aa6b2");

    // 5) ساخت چارت
    try {
      new Chart(ctx, {
        type: "line",
        data: {
          labels,
          datasets: [{
            label: "روند قیمت ماهانه",
            data: dataPoints,
            borderColor: lineColor,
            backgroundColor: "rgba(108,140,255,0.12)",
            borderWidth: 3,
            tension: 0.35,
            pointRadius: 0,
            fill: true
          }]
        },
        options: {
          locale: "fa-IR",
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              enabled: true,
              callbacks: {
                title: items => (items[0]?.label ?? ""),
                label: item => " " + faNum(item.raw) + " واحد",
              }
            }
          },
          interaction: { mode: "nearest", intersect: false },
          scales: {
            x: {
              grid: { display: false },
              ticks: {
                color: ticksColor,
                callback: (v) => labels[v] // برای RTL هم جواب می‌دهد
              }
            },
            y: {
              beginAtZero: true,
              grid: { color: gridColor },
              ticks: {
                color: ticksColor,
                stepSize: 25,
                callback: (value) => faNum(value)
              }
            }
          }
        }
      });
    } catch (_) {
      // اگر هر مشکلی بود، در پروداکشن سکوت کن
      // console.error("Chart init failed:", _);
    }
  }

  function tryJSON(s) {
    if (!s) return null;
    try { return JSON.parse(s); } catch { return null; }
  }
})();

// ======================= WISHLIST STATUS (icon + navbar count) =======================
document.addEventListener("DOMContentLoaded", function () {
    const btn = document.querySelector(".btn-wishlist");
    if (!btn) return; // اگر روی صفحه دکمه وجود نداشت

    const productId = btn.dataset.productId;
    const url = btn.dataset.statusUrl;  // باید در HTML بگذاری
    const icon = btn.querySelector("i");

    if (!productId || !url || !icon) return;

    fetch(`${url}?product_id=${productId}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" }
    })
    .then(res => res.json())
    .then(data => {
        // ست کردن آیکون
        if (data.in_wishlist) {
            icon.classList.remove("bi-heart");
            icon.classList.add("bi-heart-fill");
            btn.classList.add("added");
            btn.querySelector("span").textContent = "حذف از علاقه‌مندی‌ها";
        } else {
            icon.classList.remove("bi-heart-fill");
            icon.classList.add("bi-heart");
            btn.classList.remove("added");
            btn.querySelector("span").textContent = "افزودن به لیست علاقه‌مندی";
        }

        // آپدیت badge نوبار
        const badge = document.querySelector(".wishlist-count");
        if (badge) {
            badge.textContent = data.count ?? 0;
        }
    })
    .catch(err => console.error("Wishlist status error:", err));
});


// ------------- Compare Flag ----------------

document.addEventListener("DOMContentLoaded", function() {
    const messages = document.querySelectorAll(".flash-message");
    messages.forEach(msg => {
        // بعد 5 ثانیه شروع به کم رنگ شدن می‌کنیم
        setTimeout(() => {
            msg.style.opacity = '0';
            // بعد از اتمام انیمیشن حذف از DOM
            setTimeout(() => msg.remove(), 800);
        }, 5000);
    });
});
