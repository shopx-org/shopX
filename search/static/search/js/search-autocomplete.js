// // search/static/search/js/search-autocomplete.js
// const dropdown   = document.getElementById("search-dropdown");
// const resultsBox = document.getElementById("search-autocomplete-results");
// (function () {
//     function debounce(fn, delay) {
//         let timer = null;
//         return function () {
//             const context = this;
//             const args = arguments;
//             clearTimeout(timer);
//             timer = setTimeout(function () {
//                 fn.apply(context, args);
//             }, delay);
//         };
//     }
//
//     function initSearchAutocomplete() {
//         const input = document.getElementById("site-search-input");
//         if (!input) return;
//
//         const wrapper = input.closest(".header-search-wrapper");
//         if (!wrapper) return;
//
//         const dropdown = wrapper.querySelector("#search-dropdown");
//         if (!dropdown) return;
//
//         const suggestUrl = wrapper.dataset.suggestUrl;
//         if (!suggestUrl) return;
//
//         const form = wrapper.closest("form");
//         const searchUrlBase = form ? form.getAttribute("action") || "/search/" : "/search/";
//
//         function hideDropdown() {
//             dropdown.classList.add("d-none");
//             dropdown.innerHTML = "";
//         }
//
//         function renderDropdown(data, query) {
//             const categories = data && data.categories ? data.categories : [];
//
//             if (!categories.length) {
//                 dropdown.innerHTML =
//                     '<div class="search-suggest-empty">نتیجه‌ای برای «' +
//                     query +
//                     '» پیدا نشد.</div>';
//                 dropdown.classList.remove("d-none");
//                 return;
//             }
//
//             let html = "";
//
//             categories.forEach(function (cat) {
//                 if (!cat.products || !cat.products.length) {
//                     return;
//                 }
//
//                 html += '<div class="search-suggest-group">';
//                 html +=
//                     '<div class="search-suggest-group-title">' +
//                     cat.name +
//                     "</div>";
//
//                 cat.products.forEach(function (p) {
//                     html += '<a href="' + p.url + '" class="search-suggest-item">';
//                     if (p.thumbnail) {
//                         html +=
//                             '<div class="search-suggest-thumb"><img src="' +
//                             p.thumbnail +
//                             '" alt="' +
//                             p.name +
//                             '"></div>';
//                     } else {
//                         html += '<div class="search-suggest-thumb no-thumb"></div>';
//                     }
//                     html += '<div class="search-suggest-meta">';
//                     html +=
//                         '<div class="search-suggest-name">' +
//                         p.name +
//                         "</div>";
//                     if (p.brand) {
//                         html +=
//                             '<div class="search-suggest-brand">' +
//                             p.brand +
//                             "</div>";
//                     }
//                     html += "</div>";
//                     html += "</a>";
//                 });
//
//                 html += "</div>";
//             });
//
//             // ردیف «مشاهده همه نتایج برای ...»
//             const fullUrl =
//                 searchUrlBase +
//                 (searchUrlBase.indexOf("?") === -1 ? "?q=" : "&q=") +
//                 encodeURIComponent(query);
//
//             html +=
//                 '<div class="search-suggest-footer">' +
//                 '<a href="' +
//                 fullUrl +
//                 '" class="search-suggest-view-all">' +
//                 'مشاهده همه نتایج برای «' +
//                 query +
//                 '»' +
//                 "</a>" +
//                 "</div>";
//
//             dropdown.innerHTML = html;
//             dropdown.classList.remove("d-none");
//         }
//
//         const handleInput = debounce(function (event) {
//             const q = event.target.value.trim();
//             if (q.length < 2) {
//                 hideDropdown();
//                 return;
//             }
//
//             const url = suggestUrl + "?q=" + encodeURIComponent(q);
//
//             fetch(url, {
//                 headers: {
//                     "X-Requested-With": "XMLHttpRequest"
//                 }
//             })
//                 .then(function (res) {
//                     if (!res.ok) {
//                         throw new Error("Network response was not ok");
//                     }
//                     return res.json();
//                 })
//                 .then(function (data) {
//                     renderDropdown(data, q);
//                 })
//                 .catch(function (err) {
//                     console.error("Search suggest error:", err);
//                     hideDropdown();
//                 });
//         }, 250);
//
//         input.addEventListener("input", handleInput);
//
//         // بستن دراپ‌داون وقتی بیرون کلیک می‌کنی
//         document.addEventListener("click", function (event) {
//             if (!wrapper.contains(event.target)) {
//                 hideDropdown();
//             }
//         });
//     }
//
//     if (document.readyState === "loading") {
//         document.addEventListener("DOMContentLoaded", initSearchAutocomplete);
//     } else {
//         initSearchAutocomplete();
//     }
// })();
//
//
//     // چند انتخاب برند را به یک CSV در name=brand تبدیل می‌کند
// function toggleBrand(chk) {
//     const form = document.getElementById('brand-form');
//     const checks = form.querySelectorAll('input[name="brand"]');
//     const vals = [];
//     checks.forEach(c => {
//         if (c.checked) vals.push(c.value);
//     });
//     checks.forEach(c => c.disabled = true);
//     const hidden = document.createElement('input');
//     hidden.type = 'hidden';
//     hidden.name = 'brand';
//     hidden.value = vals.join(',');
//     form.appendChild(hidden);
// }
//
//     // تنظیم بازه قیمت از رادیویی‌های پرست
// function setRange(min, max) {
//     document.getElementById('price-min').value = (min !== '' && min !== null) ? min : '';
//     document.getElementById('price-max').value = (max !== '' && max !== null) ? max : '';
// }
//     // جمع کردن id برندهای تیک‌خورده در hidden=brand
//     function updateBrandFilter() {
//         const form = document.getElementById('filters-form');
//         const checks = form.querySelectorAll('#filter-brands input.custom-control-input[type="checkbox"]');
//         const vals = [];
//         checks.forEach(c => {
//             if (c.checked) vals.push(c.value);
//         });
//         document.getElementById('brand-hidden').value = vals.join(',');
//     }
//
//     // پاک کردن سریع همه فیلترها
//     function clearFilters(e) {
//         e.preventDefault();
//         const form = document.getElementById('filters-form');
//         form.querySelectorAll('input[type="checkbox"]').forEach(c => c.checked = false);
//         form.querySelectorAll('input[name="min"], input[name="max"]').forEach(i => i.value = "");
//         const catSel = form.querySelector('select[name="cat"]');
//         if (catSel) catSel.value = "";
//         const hiddenBrand = document.getElementById('brand-hidden');
//         if (hiddenBrand) hiddenBrand.value = "";
//         form.submit();
//     }
//
//  // آپدیت فیلتر برندها (hidden brand)
//     function updateBrandFilter() {
//         const form = document.getElementById('filters-form');
//         if (!form) return;
//         const checks = form.querySelectorAll('#filter-brands input.custom-control-input[type="checkbox"]');
//         const vals = [];
//         checks.forEach(c => {
//             if (c.checked) vals.push(c.value);
//         });
//         const hidden = document.getElementById('brand-hidden');
//         if (hidden) hidden.value = vals.join(',');
//     }
//
//     // پاک کردن همه فیلترها
//     function clearFilters(e) {
//         e.preventDefault();
//         const form = document.getElementById('filters-form');
//         if (!form) return;
//
//         form.querySelectorAll('input[type="checkbox"]').forEach(c => c.checked = false);
//         form.querySelectorAll('input[name="min"], input[name="max"]').forEach(i => i.value = "");
//         const catHidden = document.getElementById('cat-hidden');
//         if (catHidden) catHidden.value = "";
//         const brandHidden = document.getElementById('brand-hidden');
//         if (brandHidden) brandHidden.value = "";
//         form.submit();
//     }
//
//     // دراپ‌داون دسته‌بندی
//     function setupCategoryDropdown() {
//         const toggle = document.getElementById('cat-select-toggle');
//         const menu   = document.getElementById('cat-select-menu');
//         const hidden = document.getElementById('cat-hidden');
//         const label  = document.getElementById('cat-select-label');
//
//         if (!toggle || !menu || !hidden || !label) return;
//
//         // باز/بسته شدن منو
//         toggle.addEventListener('click', function (e) {
//             e.stopPropagation();
//             menu.classList.toggle('open');
//         });
//
//         // انتخاب هر گزینه
//         menu.querySelectorAll('.cat-option').forEach(function (btn) {
//             btn.addEventListener('click', function (e) {
//                 e.preventDefault();
//                 const id = this.dataset.id || "";
//                 hidden.value = id;
//
//                 // متن برچسب
//                 label.textContent = this.textContent.trim();
//
//                 // active
//                 menu.querySelectorAll('.cat-option').forEach(b => b.classList.remove('is-active'));
//                 this.classList.add('is-active');
//
//                 menu.classList.remove('open');
//             });
//         });
//
//         // بستن منو با کلیک بیرون
//         document.addEventListener('click', function (e) {
//             if (!menu.contains(e.target) && !toggle.contains(e.target)) {
//                 menu.classList.remove('open');
//             }
//         });
//     }
//
//     document.addEventListener('DOMContentLoaded', function () {
//         setupCategoryDropdown();
//     });
//
//
// document.addEventListener('DOMContentLoaded', function () {
//     const track      = document.querySelector('.price-range-track');
//     const leftHandle = track ? track.querySelector('.left-handle') : null;
//     const rightHandle= track ? track.querySelector('.right-handle') : null;
//
//     const rangeMin   = document.getElementById('price-range-min');
//     const rangeMax   = document.getElementById('price-range-max');
//
//     const inputMin   = document.querySelector('input[name="min"]');
//     const inputMax   = document.querySelector('input[name="max"]');
//
//     if (!track || !leftHandle || !rightHandle || !rangeMin || !rangeMax || !inputMin || !inputMax) {
//         return;
//     }
//
//     const baseMin = parseInt(track.dataset.min || '0', 10);
//     const baseMax = parseInt(track.dataset.max || '0', 10);
//
//     function clamp(val, min, max) {
//         val = isNaN(val) ? min : val;
//         if (val < min) return min;
//         if (val > max) return max;
//         return val;
//     }
//
//     function updateHandles(minVal, maxVal) {
//         const span = (baseMax - baseMin) || 1;
//         const leftPct  = ((minVal - baseMin) / span) * 100;
//         const rightPct = ((maxVal - baseMin) / span) * 100;
//
//         leftHandle.style.left  = leftPct  + '%';
//         rightHandle.style.left = rightPct + '%';
//     }
//
//     function syncInputsFromRanges() {
//         let minVal = parseInt(rangeMin.value, 10);
//         let maxVal = parseInt(rangeMax.value, 10);
//
//         if (minVal > maxVal) {
//             const tmp = minVal;
//             minVal = maxVal;
//             maxVal = tmp;
//         }
//
//         minVal = clamp(minVal, baseMin, baseMax);
//         maxVal = clamp(maxVal, baseMin, baseMax);
//
//         inputMin.value = minVal;
//         inputMax.value = maxVal;
//
//         updateHandles(minVal, maxVal);
//     }
//
//     function syncRangesFromInputs() {
//         let minVal = clamp(parseInt(inputMin.value || baseMin, 10), baseMin, baseMax);
//         let maxVal = clamp(parseInt(inputMax.value || baseMax, 10), baseMin, baseMax);
//
//         if (minVal > maxVal) minVal = maxVal;
//
//         rangeMin.value = minVal;
//         rangeMax.value = maxVal;
//
//         updateHandles(minVal, maxVal);
//     }
//
//     rangeMin.addEventListener('input', syncInputsFromRanges);
//     rangeMax.addEventListener('input', syncInputsFromRanges);
//
//     inputMin.addEventListener('input', syncRangesFromInputs);
//     inputMax.addEventListener('input', syncRangesFromInputs);
//
//     // مقدار اولیه
//     syncRangesFromInputs();
// });
//
// document.addEventListener('DOMContentLoaded', function () {
//     const HISTORY_KEY    = 'shopx_search_history_v1';
//     const MAX_ITEMS      = 10;
//
//     const form           = document.querySelector('#header-search-form');  // id روی فرم هدر بذار
//     const input          = form ? form.querySelector('input[name="q"]') : null;
//
//     const historySection = document.getElementById('search-history-section');
//     const historyList    = document.getElementById('search-history-list');
//     const historyClear   = document.getElementById('search-history-clear');
//
//     if (!form || !input || !historySection || !historyList || !historyClear) return;
//
//     // ---------- helpers ----------
//     function loadHistory() {
//         try {
//             const raw = localStorage.getItem(HISTORY_KEY);
//             if (!raw) return [];
//             const arr = JSON.parse(raw);
//             return Array.isArray(arr) ? arr : [];
//         } catch (e) {
//             return [];
//         }
//     }
//
//     function saveHistory(list) {
//         localStorage.setItem(HISTORY_KEY, JSON.stringify(list));
//     }
//
//     function addToHistory(term) {
//         term = (term || '').trim();
//         if (!term) return;
//         let list = loadHistory();
//
//         // تکراری را حذف کن
//         list = list.filter(x => x !== term);
//         // در ابتدای لیست بگذار
//         list.unshift(term);
//         // حداکثر N آیتم
//         if (list.length > MAX_ITEMS) {
//             list = list.slice(0, MAX_ITEMS);
//         }
//         saveHistory(list);
//     }
//
//     function renderHistory() {
//         const list = loadHistory();
//         historyList.innerHTML = '';
//
//         if (!list.length) {
//             historySection.classList.add('d-none');
//             return;
//         }
//
//         list.forEach(term => {
//             const btn = document.createElement('button');
//             btn.type = 'button';
//             btn.className = 'btn btn-sm search-history-pill';
//             btn.textContent = term;
//             btn.addEventListener('click', function () {
//                 input.value = term;
//                 form.submit();   // یا فقط input.focus() اگر نمی‌خوای مستقیم سرچ بشه
//             });
//             historyList.appendChild(btn);
//         });
//
//         historySection.classList.remove('d-none');
//     }
//
//     // ---------- events ----------
//
//     // هنگام submit فرم → اضافه به history
//     form.addEventListener('submit', function () {
//         addToHistory(input.value);
//     });
//
//     // هنگام فوکوس روی اینپوت → تاریخچه را نشان بده
//     input.addEventListener('focus', function () {
//         renderHistory();
//     });
//
//     // اگر کاربر تایپ کرد و autocomplete نتایج را نشان می‌دهد،
//     // هنوز می‌توانیم تاریخچه را کنار/زیرش نگه داریم یا مخفی کنیم:
//     input.addEventListener('input', function () {
//         renderHistory();
//     });
//
//     // پاک کردن تاریخچه
//     historyClear.addEventListener('click', function () {
//         localStorage.removeItem(HISTORY_KEY);
//         renderHistory();
//     });
//
//     // بار اول
//     renderHistory();
// });

// ============================
// ۱) اتوکامپلیت سرچ (دسکتاپ + موبایل)
// ============================
(function () {
    function debounce(fn, delay) {
        let timer = null;
        return function () {
            const context = this;
            const args = arguments;
            clearTimeout(timer);
            timer = setTimeout(function () {
                fn.apply(context, args);
            }, delay);
        };
    }

    // این تابع برای هر input جداگانه اجرا می‌شود
    function attachAutocompleteToInput(input) {
        if (!input) return;

        const wrapper = input.closest(".header-search-wrapper");
        if (!wrapper) return;

        const dropdown = wrapper.querySelector("#search-dropdown");
        if (!dropdown) return;

        const resultsBox = dropdown.querySelector("#search-autocomplete-results");
        if (!resultsBox) return;

        const suggestUrl = wrapper.dataset.suggestUrl;
        if (!suggestUrl) return;

        const form = wrapper.closest("form");
        const searchUrlBase = form ? form.getAttribute("action") || "/search/" : "/search/";

        function hideDropdown() {
            dropdown.classList.add("d-none");
            resultsBox.innerHTML = "";
        }

        function renderDropdown(data, query) {
            const categories = data && data.categories ? data.categories : [];

            if (!categories.length) {
                resultsBox.innerHTML =
                    '<div class="search-suggest-empty">نتیجه‌ای برای «' +
                    query +
                    '» پیدا نشد.</div>';
                dropdown.classList.remove("d-none");
                return;
            }

            let html = "";

            categories.forEach(function (cat) {
                if (!cat.products || !cat.products.length) return;

                html += '<div class="search-suggest-group">';
                html +=
                    '<div class="search-suggest-group-title">' +
                    cat.name +
                    "</div>";

                cat.products.forEach(function (p) {
                    html += '<a href="' + p.url + '" class="search-suggest-item">';
                    if (p.thumbnail) {
                        html +=
                            '<div class="search-suggest-thumb"><img src="' +
                            p.thumbnail +
                            '" alt="' +
                            p.name +
                            '"></div>';
                    } else {
                        html += '<div class="search-suggest-thumb no-thumb"></div>';
                    }
                    html += '<div class="search-suggest-meta">';
                    html += '<div class="search-suggest-name">' + p.name + "</div>";
                    if (p.brand) {
                        html += '<div class="search-suggest-brand">' + p.brand + "</div>";
                    }
                    html += "</div></a>";
                });

                html += "</div>";
            });

            const fullUrl =
                searchUrlBase +
                (searchUrlBase.indexOf("?") === -1 ? "?q=" : "&q=") +
                encodeURIComponent(query);

            html +=
                '<div class="search-suggest-footer">' +
                '<a href="' +
                fullUrl +
                '" class="search-suggest-view-all">' +
                'مشاهده همه نتایج برای «' +
                query +
                '»' +
                "</a>" +
                "</div>";

            resultsBox.innerHTML = html;
            dropdown.classList.remove("d-none");
        }

        const handleInput = debounce(function (event) {
            const q = event.target.value.trim();
            if (q.length < 2) {
                hideDropdown();
                return;
            }

            const url = suggestUrl + "?q=" + encodeURIComponent(q);

            fetch(url, {
                headers: { "X-Requested-With": "XMLHttpRequest" }
            })
                .then(function (res) {
                    if (!res.ok) throw new Error("Network response was not ok");
                    return res.json();
                })
                .then(function (data) {
                    renderDropdown(data, q);
                })
                .catch(function (err) {
                    console.error("Search suggest error:", err);
                    hideDropdown();
                });
        }, 250);

        input.addEventListener("input", handleInput);

        document.addEventListener("click", function (event) {
            if (!wrapper.contains(event.target)) {
                hideDropdown();
            }
        });
    }

    function initSearchAutocomplete() {
        // روی هر input که این کلاس را دارد (دسکتاپ + موبایل) اتوکامپلیت فعال کن
        const inputs = document.querySelectorAll(".js-site-search-input");
        inputs.forEach(attachAutocompleteToInput);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initSearchAutocomplete);
    } else {
        initSearchAutocomplete();
    }
})();



// ============================
// ۲) فیلتر برندها و پاک کردن فیلترها
// ============================

// آپدیت فیلتر برندها (hidden brand)
function updateBrandFilter() {
    const form = document.getElementById('filters-form');
    if (!form) return;

    const checks = form.querySelectorAll('#filter-brands input.custom-control-input[type="checkbox"]');
    const vals = [];
    checks.forEach(c => {
        if (c.checked) vals.push(c.value);
    });

    const hidden = document.getElementById('brand-hidden');
    if (hidden) {
        hidden.value = vals.join(',');
    }
}

// پاک کردن همه فیلترها
function clearFilters(e) {
    e.preventDefault();
    const form = document.getElementById('filters-form');
    if (!form) return;

    // تیک همه چک‌باکس‌ها
    form.querySelectorAll('input[type="checkbox"]').forEach(c => c.checked = false);

    // پاک کردن min/max
    form.querySelectorAll('input[name="min"], input[name="max"]').forEach(i => i.value = "");

    // دسته‌بندی
    const catHidden = document.getElementById('cat-hidden');
    if (catHidden) catHidden.value = "";

    // برند
    const brandHidden = document.getElementById('brand-hidden');
    if (brandHidden) brandHidden.value = "";

    form.submit();
}


// ============================
// ۳) دراپ‌داون دسته‌بندی کاستوم
// ============================
function setupCategoryDropdown() {
    const toggle = document.getElementById('cat-select-toggle');
    const menu   = document.getElementById('cat-select-menu');
    const hidden = document.getElementById('cat-hidden');
    const label  = document.getElementById('cat-select-label');

    if (!toggle || !menu || !hidden || !label) return;

    // باز/بسته شدن منو
    toggle.addEventListener('click', function (e) {
        e.stopPropagation();
        menu.classList.toggle('open');
    });

    // انتخاب هر گزینه
    menu.querySelectorAll('.cat-option').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            const id = this.dataset.id || "";
            hidden.value = id;

            // متن برچسب
            label.textContent = this.textContent.trim();

            // active
            menu.querySelectorAll('.cat-option').forEach(b => b.classList.remove('is-active'));
            this.classList.add('is-active');

            menu.classList.remove('open');
        });
    });

    // بستن منو با کلیک بیرون
    document.addEventListener('click', function (e) {
        if (!menu.contains(e.target) && !toggle.contains(e.target)) {
            menu.classList.remove('open');
        }
    });
}

document.addEventListener('DOMContentLoaded', function () {
    setupCategoryDropdown();
});


// ============================
// ۴) اسلایدر بازه قیمت (price range)
// ============================
document.addEventListener('DOMContentLoaded', function () {
    const track      = document.querySelector('.price-range-track');
    const leftHandle = track ? track.querySelector('.left-handle') : null;
    const rightHandle= track ? track.querySelector('.right-handle') : null;

    const rangeMin   = document.getElementById('price-range-min');
    const rangeMax   = document.getElementById('price-range-max');

    const inputMin   = document.querySelector('input[name="min"]');
    const inputMax   = document.querySelector('input[name="max"]');

    if (!track || !leftHandle || !rightHandle || !rangeMin || !rangeMax || !inputMin || !inputMax) {
        return;
    }

    const baseMin = parseInt(track.dataset.min || '0', 10);
    const baseMax = parseInt(track.dataset.max || '0', 10);

    function clamp(val, min, max) {
        val = isNaN(val) ? min : val;
        if (val < min) return min;
        if (val > max) return max;
        return val;
    }

    function updateHandles(minVal, maxVal) {
        const span = (baseMax - baseMin) || 1;
        const leftPct  = ((minVal - baseMin) / span) * 100;
        const rightPct = ((maxVal - baseMin) / span) * 100;

        leftHandle.style.left  = leftPct  + '%';
        rightHandle.style.left = rightPct + '%';
    }

    // وقتی اسلایدرها حرکت می‌کنند → اینپوت‌ها و دستگیره‌ها آپدیت شوند
    function syncInputsFromRanges() {
        let minVal = parseInt(rangeMin.value, 10);
        let maxVal = parseInt(rangeMax.value, 10);

        if (minVal > maxVal) {
            const tmp = minVal;
            minVal = maxVal;
            maxVal = tmp;
        }

        minVal = clamp(minVal, baseMin, baseMax);
        maxVal = clamp(maxVal, baseMin, baseMax);

        inputMin.value = minVal;
        inputMax.value = maxVal;

        updateHandles(minVal, maxVal);
    }

    // وقتی کاربر عدد تایپ کند → اسلایدرها و دستگیره‌ها آپدیت شوند
    function syncRangesFromInputs() {
        let minVal = clamp(parseInt(inputMin.value || baseMin, 10), baseMin, baseMax);
        let maxVal = clamp(parseInt(inputMax.value || baseMax, 10), baseMin, baseMax);

        if (minVal > maxVal) minVal = maxVal;

        rangeMin.value = minVal;
        rangeMax.value = maxVal;

        updateHandles(minVal, maxVal);
    }

    rangeMin.addEventListener('input', syncInputsFromRanges);
    rangeMax.addEventListener('input', syncInputsFromRanges);

    inputMin.addEventListener('input', syncRangesFromInputs);
    inputMax.addEventListener('input', syncRangesFromInputs);

    // مقدار اولیه
    syncRangesFromInputs();
});

// ============================
// ۵) Search History در باکس سرچ — نسخه نهایی و بدون باگ
// ============================
document.addEventListener('DOMContentLoaded', function () {
    const HISTORY_KEY    = 'shopx_search_history_v1';
    const MAX_ITEMS      = 10;

    // فقط فرم هدر
    const form           = document.querySelector('#header-search-form');
    const input          = form ? form.querySelector('input[name="q"]') : null;

    const historySection = document.getElementById('search-history-section');
    const historyList    = document.getElementById('search-history-list');
    const historyClear   = document.getElementById('search-history-clear');
    const dropdown       = form ? form.querySelector('#search-dropdown') : null;

    if (!form || !input || !historySection || !historyList) return;

    function loadHistory() {
        try {
            const raw = localStorage.getItem(HISTORY_KEY);
            return raw ? JSON.parse(raw) : [];
        } catch (e) {
            return [];
        }
    }

    function saveHistory(list) {
        localStorage.setItem(HISTORY_KEY, JSON.stringify(list.slice(0, MAX_ITEMS)));
    }

    function addToHistory(term) {
        term = term.trim();
        if (!term) return;
        let list = loadHistory();
        list = list.filter(x => x !== term);
        list.unshift(term);
        saveHistory(list);
    }

    function renderHistory() {
        const list = loadHistory();
        historyList.innerHTML = '';

        if (list.length === 0) {
            historySection.classList.add('d-none');
            return;
        }

        list.forEach(term => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-sm search-history-pill me-2 mb-2';
            btn.textContent = term;
            btn.addEventListener('click', () => {
                input.value = term;
                form.submit();
            });
            historyList.appendChild(btn);
        });

        historySection.classList.remove('d-none');

        if (dropdown && dropdown.classList.contains('d-none')) {
            dropdown.classList.remove('d-none');
        }
    }

    input.addEventListener('focus', function () {
        if (input.value.trim() === '') {
            renderHistory();
        }
    });

    input.addEventListener('input', function () {
        if (input.value.trim() === '') {
            renderHistory();
        }
    });

    form.addEventListener('submit', function () {
        addToHistory(input.value);
    });

    if (historyClear) {
        historyClear.addEventListener('click', function () {
            localStorage.removeItem(HISTORY_KEY);
            historyList.innerHTML = '';
            historySection.classList.add('d-none');
        });
    }

    document.addEventListener('click', function (e) {
        if (!form.contains(e.target)) {
            if (dropdown) dropdown.classList.add('d-none');
        }
    });
});