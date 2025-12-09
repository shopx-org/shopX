

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
  const stickyImg    = $("#sticky-img");
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
 function activateThumb(btn) {
    if (!btn || !mainImg) return;

    // آدرس تصویر بزرگ
    const full = btn.dataset.full || btn.querySelector("img")?.getAttribute("src");
    if (full) {
      mainImg.setAttribute("src", full);
      if (stickyImg) {
        stickyImg.setAttribute("src", full);
      }
    }

    // کلاس active + aria-pressed روی تامب‌ها
    $$(".thumb").forEach(t => {
      const isActive = t === btn;
      t.classList.toggle("is-active", isActive);
      t.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
  }

 function swapImageForColor(colorId) {
    if (!colorId) return;
    // سعی می‌کنیم تامبی پیدا کنیم که رنگش با colorId یکی است
    let btn = document.querySelector(`.thumb[data-color-id="${colorId}"]`);
    // اگر نبود، حداقل اولین تامب را فعال کن
    if (!btn) {
      btn = document.querySelector(".thumb");
    }
    if (btn) {
      activateThumb(btn);
    }
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

  // گالری تصاویر: کلیک روی تامب‌ها
  $$(".thumbs .thumb").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      activateThumb(btn);
    });
  });

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

// ================== Price History Chart ==================
function initPriceChart() {
  const jsonScript = document.getElementById("price-chart-data");
  const canvas = document.getElementById("priceLineChart");
  const card = document.querySelector("#line-chart");

  if (!jsonScript || !canvas) return;

  let chartData;
  try {
    chartData = JSON.parse(jsonScript.textContent || "{}");
  } catch (e) {
    console.error("price-chart-data JSON parse error", e);
    return;
  }

  const labelsRaw = chartData.labels || [];
  const minPrices = chartData.min_prices || [];
  const avgPrices = chartData.avg_prices || [];

  if (!labelsRaw.length || (!minPrices.length && !avgPrices.length)) {
    if (card) {
      card.innerHTML =
        '<div class="p-3 text-muted" style="font-size:0.9rem;">برای این محصول هنوز سابقهٔ قیمت ثبت نشده است.</div>';
    }
    return;
  }

  // تبدیل تاریخ‌ها به فرمت فارسی قابل‌خواندن
  const labels = labelsRaw.map((d) => {
    try {
      const dt = new Date(d);
      return dt.toLocaleDateString("fa-IR");
    } catch (e) {
      return d;
    }
  });

  const rootStyles = getComputedStyle(document.documentElement);
  const colorMin =
    rootStyles.getPropertyValue("--chart-min").trim() ||
    rootStyles.getPropertyValue("--line").trim() ||
    "#2563eb"; // آبی
  const colorAvg =
    rootStyles.getPropertyValue("--chart-avg").trim() ||
    "#22c55e"; // سبز
  const gridColor =
    rootStyles.getPropertyValue("--grid").trim() || "#eff3f8";
  const axisColor =
    rootStyles.getPropertyValue("--axis-muted").trim() || "#9ca3af";
  const fillBg =
    rootStyles.getPropertyValue("--chart-fill").trim() || "rgba(250,106,53,0.08)";

  const meta = chartData.meta || {};
  const minY = meta.min_y ?? meta.min_overall;
  const maxY = meta.max_y ?? meta.max_overall;

  const ctx = canvas.getContext("2d");

  if (canvas._priceChartInstance) {
    canvas._priceChartInstance.destroy();
  }

  const datasets = [];

  if (minPrices.length) {
    datasets.push({
      label: "کمترین قیمت",
      data: minPrices,
      borderColor: colorMin,
      backgroundColor: colorMin,
      pointBackgroundColor: colorMin,
      pointRadius: 3,
      pointHoverRadius: 4,
      borderWidth: 2,
      tension: 0.3,
    });
  }

  if (avgPrices.length) {
    datasets.push({
      label: "میانگین قیمت",
      data: avgPrices,
      borderColor: colorAvg,
      backgroundColor: fillBg, // برای fill زیر منحنی
      pointBackgroundColor: colorAvg,
      pointRadius: 3,
      pointHoverRadius: 4,
      borderWidth: 2,
      tension: 0.3,
      fill: "origin",
    });
  }

  const chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: datasets,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          labels: {
            usePointStyle: true,
            boxWidth: 8,
            boxHeight: 8,
          },
        },
        tooltip: {
          callbacks: {
            label: function (ctx) {
              const val = ctx.parsed.y || 0;
              const title = ctx.dataset.label || "";
              return (
                title +
                ": " +
                val.toLocaleString("fa-IR") +
                " تومان"
              );
            },
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            color: axisColor,
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: 6,
          },
        },
        y: {
          grid: { color: gridColor },
          ticks: {
            color: axisColor,
            callback: function (value) {
              return value.toLocaleString("fa-IR");
            },
          },
          // محور Y بین کمترین و بیشترین قیمت (با کمی حاشیه)
          min: typeof minY === "number" ? minY : undefined,
          max: typeof maxY === "number" ? maxY : undefined,
        },
      },
    },
  });

  canvas._priceChartInstance = chart;
}

document.addEventListener("DOMContentLoaded", function () {
  initPriceChart();
});