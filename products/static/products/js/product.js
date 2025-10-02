// ======================= گالری + لایت‌باکس =======================
(function () {
    var gallerySel = '.tlp-gallery.gallery-rtl-right, .tlp-gallery.gallery-amz-left';
    var gallery = document.querySelector(gallerySel);
    if (!gallery) return;

    var stageBox = gallery.querySelector('.stage');
    var stageImg = stageBox ? (stageBox.querySelector('img') || document.getElementById('tlp-main')) : null;
    var thumbsWrap = gallery.querySelector('.thumbs');
    var thumbs = thumbsWrap ? Array.from(thumbsWrap.querySelectorAll('.thumb')) : [];
    if (!stageBox || !stageImg || !thumbs.length) return;

    // -- helpers
    function fullFrom(btn) {
        var df = btn.getAttribute('data-full');
        if (df) return df;
        var img = btn.querySelector('img');
        return img && img.src ? img.src.replace('-small', '') : '';
    }

    function activate(btn) {
        thumbs.forEach(function (t) {
            t.classList.remove('is-active');
        });
        btn.classList.add('is-active');
        var full = fullFrom(btn);
        if (full) stageImg.src = full;
    }

    // preload
    thumbs.forEach(function (btn) {
        var f = fullFrom(btn);
        if (f) {
            var pre = new Image();
            pre.src = f;
        }
    });

    // interactions
    thumbs.forEach(function (btn) {
        btn.addEventListener('mouseenter', function () {
            activate(btn);
        });
        btn.addEventListener('focus', function () {
            activate(btn);
        });
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            activate(btn);
        });
    });

    // +N more
    var MAX_VISIBLE = 5, moreBtn = null;
    if (thumbs.length > MAX_VISIBLE) {
        var hidden = thumbs.slice(MAX_VISIBLE);
        hidden.forEach(function (b) {
            b.classList.add('is-hidden');
        });
        moreBtn = document.createElement('button');
        moreBtn.type = 'button';
        moreBtn.className = 'thumb thumb-more';
        moreBtn.innerHTML = '<span>+' + hidden.length + '</span>';
        thumbsWrap.appendChild(moreBtn);
    }

    // Lightbox (ساخت در صورت نبود)
    function ensureLightbox() {
        var el = document.getElementById('amz-lightbox');
        if (el) return el;
        var wrapper = document.createElement('div');
        wrapper.id = 'amz-lightbox';
        wrapper.className = 'amz-lightbox';
        wrapper.setAttribute('aria-hidden', 'true');
        wrapper.setAttribute('role', 'dialog');
        wrapper.setAttribute('aria-modal', 'true');
        wrapper.innerHTML =
            '<div class="amz-backdrop" data-close></div>'
            + '<div class="amz-modal" role="document">'
            + '  <button class="amz-close" type="button" aria-label="بستن" data-close>&times;</button>'
            + '  <button class="amz-nav prev" type="button" aria-label="قبلی">‹</button>'
            + '  <figure class="amz-stage"><img alt=""></figure>'
            + '  <button class="amz-nav next" type="button" aria-label="بعدی">›</button>'
            + '  <div class="amz-thumbs" role="tablist" aria-label="تصاویر بیشتر"></div>'
            + '</div>';
        document.body.appendChild(wrapper);
        return wrapper;
    }

    var lb = ensureLightbox();
    var lbStage = lb.querySelector('.amz-stage img');
    var lbThumbs = lb.querySelector('.amz-thumbs');
    var btnPrev = lb.querySelector('.amz-nav.prev');
    var btnNext = lb.querySelector('.amz-nav.next');
    var btnCloseEls = lb.querySelectorAll('[data-close]');
    var idx = 0, keyHandler;

    function imagesList() {
        return thumbs.map(function (t) {
            var img = t.querySelector('img');
            return {
                full: fullFrom(t),
                thumb: img ? img.src : fullFrom(t),
                alt: img ? (img.getAttribute('alt') || 'تصویر محصول') : 'تصویر محصول'
            };
        });
    }

    var images = imagesList();

    function show(i) {
        images = imagesList();
        idx = (i + images.length) % images.length;
        lbStage.src = images[idx].full;
        lbStage.alt = images[idx].alt;
        Array.from(lbThumbs.children).forEach(function (el, j) {
            el.classList.toggle('is-active', j === idx);
        });
    }

    function buildThumbs() {
        lbThumbs.innerHTML = '';
        images.forEach(function (o, i) {
            var b = document.createElement('button');
            b.type = 'button';
            b.className = 'lb-thumb' + (i === idx ? ' is-active' : '');
            b.innerHTML = '<img src="' + o.thumb + '" alt="">';
            b.addEventListener('click', function () {
                show(i);
            });
            lbThumbs.appendChild(b);
        });
    }

    function openLightbox() {
        var active = thumbs.findIndex(function (t) {
            return t.classList.contains('is-active');
        });
        idx = active > -1 ? active : 0;
        buildThumbs();
        show(idx);
        lb.classList.add('show');
        lb.setAttribute('aria-hidden', 'false');
        document.body.classList.add('no-scroll');
        keyHandler = function (e) {
            if (e.key === 'Escape') closeLightbox();
            else if (e.key === 'ArrowLeft') show(idx - 1);
            else if (e.key === 'ArrowRight') show(idx + 1);
        };
        document.addEventListener('keydown', keyHandler);
    }

    function closeLightbox() {
        lb.classList.remove('show');
        lb.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('no-scroll');
        if (keyHandler) {
            document.removeEventListener('keydown', keyHandler);
            keyHandler = null;
        }
    }

    btnPrev.addEventListener('click', function () {
        show(idx - 1);
    });
    btnNext.addEventListener('click', function () {
        show(idx + 1);
    });
    btnCloseEls.forEach(function (el) {
        el.addEventListener('click', closeLightbox);
    });
    if (moreBtn) moreBtn.addEventListener('click', openLightbox);
    stageBox.addEventListener('click', openLightbox);
})();

// ======================= زوم سبک والمارت (پنجره کناری + لنز مینیمال) =======================
(function () {
    var gallerySel = '.tlp-gallery.gallery-rtl-right, .tlp-gallery.gallery-amz-left';
    var gallery = document.querySelector(gallerySel);
    if (!gallery) return;

    var stageBox = gallery.querySelector('.stage');
    var stageImg = stageBox ? (stageBox.querySelector('img') || document.getElementById('tlp-main')) : null;
    if (!stageBox || !stageImg) return;

    var ZOOM = 2.5;   // ضریب زوم
    var GAP = 12;  // فاصله پنجره زوم از استیج

    var lens, zoomBox, zoomImg;

    function ensureParts() {
        if (!lens) {
            lens = document.createElement('div');
            lens.className = 'zoom-lens';
            stageBox.appendChild(lens);
        }
        if (!zoomBox) {
            zoomBox = document.createElement('div');
            zoomBox.className = 'zoom-box';
            zoomImg = document.createElement('div');
            zoomImg.className = 'zoom-img';
            zoomBox.appendChild(zoomImg);
            document.body.appendChild(zoomBox);
        }
    }

    function rects() {
        var sR = stageBox.getBoundingClientRect();
        var iR = stageImg.getBoundingClientRect(); // محدوده واقعی تصویر (object-fit: contain)
        return {sR, iR};
    }

    function placeZoomBox() {
        var r = rects();
        var vw = window.innerWidth, vh = window.innerHeight;
        var zbW = zoomBox.offsetWidth, zbH = zoomBox.offsetHeight;

        // RTL: اول تلاش می‌کنیم سمت «چپ» استیج جا بدهیم؛ اگر جا نبود، سمت راست
        var leftCandidate = r.sR.left - GAP - zbW;
        var top = Math.max(8, Math.min(vh - zbH - 8, r.sR.top + (r.sR.height - zbH) / 2));
        var left = (leftCandidate >= 8) ? leftCandidate : Math.min(vw - zbW - 8, r.sR.right + GAP);
        zoomBox.style.left = left + 'px';
        zoomBox.style.top = top + 'px';
    }

    function startZoom(e) {
        ensureParts();

        // نمایش قبل از اندازه‌گیری
        stageBox.classList.add('zooming');
        zoomBox.classList.add('show');

        // بک‌گراند زوم از تصویر اصلی
        zoomImg.style.backgroundImage = 'url("' + stageImg.src + '")';

        var r = rects();
        var dispW = r.iR.width, dispH = r.iR.height;

        // اندازه واقعی پنجره زوم
        var zbW = zoomBox.offsetWidth, zbH = zoomBox.offsetHeight;

        // ابعاد لنز = اندازه پنجره / ZOOM (اما نه بزرگ‌تر از خودِ تصویر نمایش‌داده‌شده)
        var lensW = Math.min(dispW, zbW / ZOOM);
        var lensH = Math.min(dispH, zbH / ZOOM);
        lens.style.width = lensW + 'px';
        lens.style.height = lensH + 'px';

        // سایز بک‌گراند متناسب با بزرگنمایی
        zoomImg.style.backgroundSize = (dispW * ZOOM) + 'px ' + (dispH * ZOOM) + 'px';

        placeZoomBox();
        if (e) onMove(e); // لنز زیر موس
    }

    function stopZoom() {
        if (zoomBox) zoomBox.classList.remove('show');
        if (stageBox) stageBox.classList.remove('zooming');
    }

    function onMove(e) {
        var r = rects();

        // آفست لبه‌های تصویر نسبت به استیج (برای object-fit: contain)
        var offX = r.iR.left - r.sR.left;
        var offY = r.iR.top - r.sR.top;
        var dispW = r.iR.width, dispH = r.iR.height;

        var lensW = lens.offsetWidth, lensH = lens.offsetHeight;

        // موقعیت موس نسبت به استیج
        var x = e.clientX - r.sR.left;
        var y = e.clientY - r.sR.top;

        // محدودسازی حرکت لنز به داخلِ خود «تصویر»
        var minX = offX + lensW / 2, maxX = offX + dispW - lensW / 2;
        var minY = offY + lensH / 2, maxY = offY + dispH - lensH / 2;
        x = Math.max(minX, Math.min(maxX, x));
        y = Math.max(minY, Math.min(maxY, y));

        // لنز دقیقا زیر نشانگر قرار می‌گیرد
        lens.style.transform = 'translate(' + (x - lensW / 2) + 'px,' + (y - lensH / 2) + 'px)';

        // مرکز لنز = مرکزِ پنجره زوم
        var zbW = zoomBox.offsetWidth, zbH = zoomBox.offsetHeight;
        var bgX = -((x - offX) * ZOOM - zbW / 2);
        var bgY = -((y - offY) * ZOOM - zbH / 2);
        zoomImg.style.backgroundPosition = bgX + 'px ' + bgY + 'px';
    }

    // رویدادها
    stageBox.addEventListener('mouseenter', function (e) {
        startZoom(e);
    });
    stageBox.addEventListener('mousemove', function (e) {
        if (!zoomBox || !zoomBox.classList.contains('show')) return;
        onMove(e);
    });
    stageBox.addEventListener('mouseleave', stopZoom, {passive: true});
    stageBox.addEventListener('touchend', stopZoom, {passive: true});
    window.addEventListener('resize', function () {
        if (zoomBox && zoomBox.classList.contains('show')) placeZoomBox();
    });
    window.addEventListener('scroll', function () {
        if (zoomBox && zoomBox.classList.contains('show')) placeZoomBox();
    }, {passive: true});
})();

// ======================= آکاردئون‌های سویچ‌دار =======================
(function () {
    document.querySelectorAll('.dk-acc').forEach(function (acc) {
        var sw = acc.querySelector('summary .switch input');
        if (!sw) return;

        function sync() {
            acc.open = !!sw.checked;
            acc.querySelectorAll('.dk-acc-body input:not([type="checkbox"][id$="-toggle"])')
                .forEach(function (i) {
                    i.disabled = !sw.checked;
                });
        }

        sw.addEventListener('change', sync);
        sync();
    });
})();

(function () {
    // منوی صفحه‌ی محصول
    const nav = document.getElementById('nav-serialscrolling');
    if (!nav) return;

    // ارتفاع هدر چسبان
    function getOffset() {
        // هر کدام از هدرهای تو که وجود دارد:
        const sticky = document.querySelector('.header-bottom.sticky-header, .header_aera, .tlp-sticky');
        return sticky ? sticky.getBoundingClientRect().height : parseInt(getComputedStyle(document.documentElement).getPropertyValue('--sticky-offset')) || 0;
    }

    function findTarget(el) {
        // اگر a با هش بود
        if (el.tagName === 'A') {
            const href = el.getAttribute('href') || '';
            if (href.startsWith('#') && href.length > 1) {
                return document.getElementById(href.slice(1));
            }
        }
        // اگر li دارای data-serialscrolling بود
        const li = el.closest('[data-serialscrolling]');
        if (li) {
            const sel = `[data-serialscrolling-target="${li.dataset.serialscrolling}"]`;
            return document.querySelector(sel);
        }
        return null;
    }

    function smoothTo(target) {
        const top = target.getBoundingClientRect().top + window.pageYOffset - getOffset() - 8;
        window.scrollTo({top, behavior: 'smooth'});
    }

    // هایلایت آیتم فعال
    function setActive(li) {
        nav.querySelectorAll('.is-current').forEach(x => x.classList.remove('is-current'));
        li.classList.add('is-current');
    }

    nav.addEventListener('click', function (e) {
        const a = e.target.closest('a, [data-serialscrolling]');
        if (!a) return;
        const target = findTarget(a);
        if (!target) return;

        e.preventDefault(); // نذار پلاگین‌ها رفتار را خراب کنند
        smoothTo(target);
        const li = a.closest('li') || a;
        setActive(li);
    });

})();


// border js //
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

    // اگر بعداً داده‌ها را از بک‌اند آوردی، فقط این تابع را صدا بزن:
    // window.updatePriceChart = (labelsFa, values) => { chart.data.labels = labelsFa; chart.data.datasets[0].data = values; chart.update(); };

})();

(function () {
  'use strict';

  // ---------- Helpers ----------
  const $  = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function readJSON(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    try { return JSON.parse(el.textContent || el.innerText || 'null'); }
    catch (_e) { return null; }
  }

  function formatFA(n) {
    if (typeof n === 'number' && typeof Intl !== 'undefined') {
      try { return new Intl.NumberFormat('fa-IR').format(n); } catch (_e) {}
    }
    return (n == null ? '' : String(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }

  // ---------- Gallery (stage + thumbs) ----------
  (function initGallery(){
    const stage  = $('#tlp-main');
    const thumbs = $$('.thumbs .thumb');
    if (!stage || !thumbs.length) return;

    thumbs.forEach(btn => {
      btn.addEventListener('click', function () {
        thumbs.forEach(b => {
          b.classList.remove('is-active');
          b.setAttribute('aria-pressed', 'false');
        });
        btn.classList.add('is-active');
        btn.setAttribute('aria-pressed', 'true');

        const full = btn.getAttribute('data-full') || $('img', btn)?.getAttribute('src');
        if (full) stage.src = full;

        const alt = $('img', btn)?.getAttribute('alt');
        if (alt) stage.alt = alt;
      });
    });
  })();

  // ---------- Variant matrix (price/stock per color+size) ----------
  const VM = readJSON('variant-matrix'); // ساختار پیشنهادی: { "<color_id>": { "<size>": {price, stock, sku, compare_at?} } }

  (function initVariants(){
    const swatches   = $$('#color-swatches a[data-color-id]');
    const sizeSelect = $('#size');
    const priceNum   = $('#price-num');
    const compareNum = $('#compare-num');
    const lowStockEl = $('.low-stock');

    let activeColorId = swatches.find(a => a.classList.contains('active'))?.getAttribute('data-color-id')
                         || (swatches[0]?.getAttribute('data-color-id') ?? null);
    let activeSize = (sizeSelect && sizeSelect.value && sizeSelect.value !== '#') ? sizeSelect.value : null;

    function updateByVariant() {
      if (!VM || !activeColorId) return;

      const byColor = VM[String(activeColorId)] || {};
      // اگر سایز انتخاب نشده بود، اولین کلید سایز را بردار
      const sizeKey = activeSize || Object.keys(byColor)[0];
      const cell = byColor[sizeKey];
      if (!cell) return;

      if (priceNum && typeof cell.price !== 'undefined') {
        priceNum.textContent = formatFA(cell.price);
      }
      if (compareNum && typeof cell.compare_at !== 'undefined') {
        compareNum.textContent = formatFA(cell.compare_at);
      }
      if (lowStockEl) {
        if (cell.stock > 0 && cell.stock <= 5) {
          lowStockEl.style.display = '';
          lowStockEl.textContent = 'تنها ' + formatFA(cell.stock) + ' عدد در انبار باقی مانده';
        } else {
          lowStockEl.style.display = 'none';
        }
      }
    }

    // کلیک روی سواچ رنگ
    if (swatches.length) {
      swatches.forEach(a => {
        a.addEventListener('click', function (e) {
          e.preventDefault();
          swatches.forEach(x => x.classList.remove('active'));
          a.classList.add('active');
          activeColorId = a.getAttribute('data-color-id');
          updateByVariant();
        });
      });
    }

    // تغییر سایز
    if (sizeSelect) {
      sizeSelect.addEventListener('change', function (e) {
        const v = e.target.value;
        activeSize = (v && v !== '#') ? v : null;
        updateByVariant();
      });
    }

    // مقداردهی اولیه
    updateByVariant();
  })();

  // ---------- Price Chart (optional) ----------
  (function initChart(){
    const data = readJSON('price-chart-data');
    const cvs  = document.getElementById('priceLineChart');
    if (!data || !cvs || typeof Chart === 'undefined') return;

    try {
      new Chart(cvs.getContext('2d'), {
        type: 'line',
        data: {
          labels: data.labels || [],
          datasets: [{
            label: 'قیمت',
            data: data.data || [],
            tension: 0.3
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: {
            y: {
              ticks: { callback: v => formatFA(v) }
            }
          }
        }
      });
    } catch (err) { console.warn('Chart init failed:', err); }
  })();

  // ---------- Prevent dummy links ----------
  $$('a[href="#"]').forEach(a => a.addEventListener('click', e => e.preventDefault()));

})();