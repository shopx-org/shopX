

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
    const faNum = n => Number(n).toLocaleString('fa-IR');

    // لیبل ماه‌ها (RTL)
    const labels = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر'];

    // داده‌ی نمونه (می‌تونی بعداً از بک‌اند تزریق کنی)
    const dataPoints = [12, 42, 36, 50, 49, 61, 68, 92, 150];

    const ctx = document.getElementById('priceLineChart').getContext('2d');

    // ایجاد چارت
    new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'روند قیمت ماهانه',
                data: dataPoints,
                borderColor: getComputedStyle(document.documentElement).getPropertyValue('--line').trim() || '#6c8cff',
                backgroundColor: 'rgba(108,140,255,0.12)',
                borderWidth: 3,
                tension: 0.35,          // خط نرم
                pointRadius: 0,         // بدون نقاط
                fill: true
            }]
        },
        options: {
            locale: 'fa-IR',
            maintainAspectRatio: false,
            plugins: {
                legend: {display: false},
                tooltip: {
                    enabled: true,
                    callbacks: {
                        title: items => items[0].label,
                        label: item => ' ' + faNum(item.raw) + ' واحد'
                    }
                }
            },
            interaction: {mode: 'nearest', intersect: false},
            scales: {
                x: {
                    grid: {display: false},
                    ticks: {
                        callback: v => labels[v],
                        color: getComputedStyle(document.documentElement).getPropertyValue('--axis-muted').trim() || '#9aa6b2'
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {color: getComputedStyle(document.documentElement).getPropertyValue('--grid').trim() || '#eff3f8'},
                    ticks: {
                        stepSize: 25,
                        color: getComputedStyle(document.documentElement).getPropertyValue('--axis-muted').trim() || '#9aa6b2',
                        callback: (value) => faNum(value)
                    }
                }
            }
        }
    });
    })();
