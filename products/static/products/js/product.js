// /* ======================= PRODUCT: Variant + Price + Gallery + Zoom + Modal + Wishlist + Chart ======================= */
// (function () {
//   "use strict";
//
//   // ---------- helpers ----------
//   const $ = (sel, root = document) => root.querySelector(sel);
//   const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
//
//   const intcomma = (n) => (Number.isFinite(n) ? n.toLocaleString("fa-IR") : "");
//
//   function readJSON(id) {
//     const el = document.getElementById(id);
//     if (!el) return null;
//     try {
//       return JSON.parse(el.textContent || el.innerText || "null");
//     } catch {
//       return null;
//     }
//   }
//
//   // ---------- elements ----------
//   const form = $("#add-to-cart-form");
//   const hiddenVid = $("#variant_id");
//   const btnAdd = $("#btn-add");
//   const qtyInput = $("#qty");
//   const colorWrap = $("#color-swatches");
//   const sizeSelect = $("#size");
//
//   // gallery
//   const stage = $("#tlp-stage") || $(".tlp-gallery .stage");
//   const mainImg = $("#tlp-main");
//   const stickyImg = $("#sticky-img");
//   const thumbsRoot = $(".thumbs");
//
//   // price UI
//   const elPriceNum = $("#price-num");
//   const elCompareNum = $("#compare-num");
//   const elSaveBox = $("#price-save");
//   const elOffBadge = $("#off-badge");
//   const elOffAmount = $("#off-amount");
//   const lowStockEl = $(".low-stock");
//
//   const priceApi = $("#price-api")?.dataset?.url || null;
//
//   // ---------- data ----------
//   const matrixObj = readJSON("variant-matrix") || {};
//   const vprices = readJSON("variant-prices") || {}; // ✅ باید تو template اضافه شه
//   const M = matrixObj.matrix || {};
//
//   // ---------- initial UI snapshot (to avoid discount flicker) ----------
//   const initialUI = {
//     priceNum: elPriceNum ? elPriceNum.textContent : "",
//     compareNum: elCompareNum ? elCompareNum.textContent : "",
//     saveDisplay: elSaveBox ? elSaveBox.style.display : "",
//     offBadge: elOffBadge ? elOffBadge.textContent : "",
//     offAmount: elOffAmount ? elOffAmount.textContent : "",
//   };
//
//   // تا وقتی دیتای معتبر نیومده، اجازه نداریم تخفیف سرور رو خاموش کنیم
//   let discountUILocked = true;
//
//   function setPriceUI({ finalPrice, basePrice, discountPercent, discountAmount }, { allowHideDiscount = true } = {}) {
//     if (elPriceNum) elPriceNum.textContent = intcomma(finalPrice || 0);
//
//     if (!elSaveBox || !elCompareNum || !elOffBadge || !elOffAmount) return;
//
//     const hasDiscount = !!(basePrice && finalPrice && finalPrice < basePrice);
//
//     if (hasDiscount) {
//       elCompareNum.textContent = intcomma(basePrice);
//       elOffBadge.textContent = `${Math.round(discountPercent || 0)}٪ تخفیف`;
//       elOffAmount.textContent = discountAmount
//         ? `مبلغ کسرشده: ${intcomma(discountAmount)} تومان`
//         : "";
//       elSaveBox.style.display = "";
//       return;
//     }
//
//     // ❗️نکته مهم: اگر قفل داریم، تخفیف رو hide نکن
//     if (!allowHideDiscount) {
//       // هیچ کاری نکن؛ همون UI سرور بمونه
//       return;
//     }
//
//     elSaveBox.style.display = "none";
//     elCompareNum.textContent = "";
//     elOffBadge.textContent = "";
//     elOffAmount.textContent = "";
//   }
//
//   function enableAdd(enabled) {
//     if (!btnAdd) return;
//     btnAdd.disabled = !enabled;
//     btnAdd.classList.toggle("is-disabled", !enabled);
//     btnAdd.setAttribute("aria-disabled", (!enabled).toString());
//   }
//
//   function updateLowStock(stock) {
//     if (!lowStockEl) return;
//     if (stock > 0 && stock <= 5) {
//       lowStockEl.style.display = "";
//       lowStockEl.textContent = "تنها " + intcomma(stock) + " عدد در انبار باقی مانده";
//     } else {
//       lowStockEl.style.display = "none";
//     }
//   }
//
//   // ---------- variant resolution ----------
//   function isSizeRequired(colorId) {
//     const row = M[String(colorId)] || {};
//     const keys = Object.keys(row);
//     if (!keys.length) return false;
//     return !(keys.length === 1 && keys[0] === "OS");
//   }
//
//   function resolveVariantCell(colorId, sizeId) {
//     if (!colorId) return null;
//     const row = M[String(colorId)] || {};
//     const key = sizeId || (row["OS"] ? "OS" : Object.keys(row)[0]);
//     if (!key) return null;
//     return row[String(key)] || null;
//   }
//
//   function resolveVariantId(colorId, sizeId) {
//     const cell = resolveVariantCell(colorId, sizeId);
//     if (!cell) return null;
//     if (cell.variant_id) return String(cell.variant_id);
//
//     // fallback by sku match
//     if (cell.sku) {
//       const matches = Object.entries(vprices).filter(([, v]) => (v && v.sku) === cell.sku);
//       if (matches.length === 1) return String(matches[0][0]);
//     }
//     return null;
//   }
//
//   // ---------- pricing ----------
//   function optimisticUpdate(variantId, cell) {
//     const cached = vprices[String(variantId)] || cell || {};
//     const finalPrice = Number(cached.price ?? 0);
//
//     // compare_at ممکنه اصلاً نیاد. اگر نیومده، "حق نداری" تخفیف رو خاموش کنی
//     const baseCandidate = cached.compare_at ?? cached.price_base ?? null;
//     const basePrice = baseCandidate == null ? null : Number(baseCandidate);
//
//     if (basePrice && finalPrice && finalPrice < basePrice) {
//       const discountAmount = basePrice - finalPrice;
//       const discountPercent = (discountAmount / basePrice) * 100;
//       setPriceUI(
//         { finalPrice, basePrice, discountPercent, discountAmount },
//         { allowHideDiscount: true }
//       );
//     } else {
//       // اینجا تخفیف رو hide نکن مگر اینکه قفل برداشته شده باشه
//       setPriceUI(
//         { finalPrice, basePrice: null, discountPercent: null, discountAmount: null },
//         { allowHideDiscount: !discountUILocked }
//       );
//     }
//   }
//
//   async function fetchAndFix(variantId) {
//     if (!priceApi || !variantId) return;
//
//     try {
//       const url = new URL(priceApi, window.location.origin);
//       url.searchParams.set("variant", String(variantId));
//       const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
//       if (!res.ok) return;
//
//       const data = await res.json();
//       if (!data || data.ok === false) return;
//
//       // وقتی دیتای دقیق اومد، دیگه قفل برداشته می‌شه
//       discountUILocked = false;
//
//       setPriceUI(
//         {
//           finalPrice: Number(data.price_final ?? 0),
//           basePrice: data.price_base ?? null,
//           discountPercent: data.discount_percent ?? null,
//           discountAmount: data.discount_amount ?? null,
//         },
//         { allowHideDiscount: true }
//       );
//     } catch {
//       // silent
//     }
//   }
//
//   // ---------- Zoom ----------
//   const Zoom = (function () {
//     const zoomBox = $("#tlp-zoom-box");
//     const zoomImgEl = $("#tlp-zoom-img");
//     const lens = stage ? $(".zoom-lens", stage) : null;
//
//     if (!stage || !mainImg || !lens || !zoomBox || !zoomImgEl) {
//       return { sync() {}, close() {}, isActive() { return false; } };
//     }
//
//     const canHover = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
//     if (!canHover) {
//       return { sync() {}, close() {}, isActive() { return false; } };
//     }
//
//     let natW = 0, natH = 0;
//
//     function getZoomSrc() {
//       return mainImg.dataset.zoomSrc || mainImg.currentSrc || mainImg.src;
//     }
//
//     function preloadNatural(src) {
//       return new Promise((resolve) => {
//         const im = new Image();
//         im.onload = () => resolve({ w: im.naturalWidth || 0, h: im.naturalHeight || 0 });
//         im.onerror = () => resolve({ w: 0, h: 0 });
//         im.src = src;
//       });
//     }
//
//     async function refreshZoomSource() {
//       const src = getZoomSrc();
//       const nat = await preloadNatural(src);
//       natW = nat.w; natH = nat.h;
//       zoomImgEl.style.backgroundImage = `url("${src}")`;
//     }
//
//     function placeZoomBox() {
//       const r = stage.getBoundingClientRect();
//       const gap = 14;
//
//       const boxW = zoomBox.offsetWidth || 420;
//       const boxH = zoomBox.offsetHeight || 420;
//
//       let left = r.left - gap - boxW; // RTL: prefer left
//       if (left < 8) left = r.right + gap;
//
//       let top = r.top;
//       const maxTop = window.innerHeight - boxH - 8;
//       if (top > maxTop) top = Math.max(8, maxTop);
//
//       zoomBox.style.left = `${left}px`;
//       zoomBox.style.top = `${top}px`;
//     }
//
//     function clamp2(v, min, max) {
//       return Math.max(min, Math.min(max, v));
//     }
//
//     function update(e) {
//       const imgRect = mainImg.getBoundingClientRect();
//       const x = e.clientX - imgRect.left;
//       const y = e.clientY - imgRect.top;
//       if (x < 0 || y < 0 || x > imgRect.width || y > imgRect.height) return;
//
//       const lensW = Math.max(90, imgRect.width * 0.35);
//       const lensH = Math.max(90, imgRect.height * 0.35);
//       lens.style.width = `${lensW}px`;
//       lens.style.height = `${lensH}px`;
//
//       const lensLeft = clamp2(x - lensW / 2, 0, imgRect.width - lensW);
//       const lensTop = clamp2(y - lensH / 2, 0, imgRect.height - lensH);
//
//       const stageRect = stage.getBoundingClientRect();
//       const leftOnStage = (imgRect.left - stageRect.left) + lensLeft;
//       const topOnStage = (imgRect.top - stageRect.top) + lensTop;
//       lens.style.transform = `translate(${leftOnStage}px, ${topOnStage}px)`;
//
//       const px = (lensLeft + lensW / 2) / imgRect.width;
//       const py = (lensTop + lensH / 2) / imgRect.height;
//
//       const bgW = natW || (imgRect.width * 3);
//       const bgH = natH || (imgRect.height * 3);
//       zoomImgEl.style.backgroundSize = `${bgW}px ${bgH}px`;
//
//       const boxW = zoomBox.clientWidth || 420;
//       const boxH = zoomBox.clientHeight || 420;
//
//       const cx = px * bgW;
//       const cy = py * bgH;
//
//       const bgLeft = clamp2(cx - boxW / 2, 0, Math.max(0, bgW - boxW));
//       const bgTop = clamp2(cy - boxH / 2, 0, Math.max(0, bgH - boxH));
//
//       zoomImgEl.style.backgroundPosition = `-${bgLeft}px -${bgTop}px`;
//     }
//
//     async function onEnter() {
//       await refreshZoomSource();
//       stage.classList.add("zooming");
//       zoomBox.classList.add("show");
//       placeZoomBox();
//     }
//
//     function onLeave() {
//       stage.classList.remove("zooming");
//       zoomBox.classList.remove("show");
//     }
//
//     stage.addEventListener("mouseenter", onEnter);
//     stage.addEventListener("mousemove", update);
//     stage.addEventListener("mouseleave", onLeave);
//
//     window.addEventListener("scroll", () => zoomBox.classList.contains("show") && placeZoomBox(), { passive: true });
//     window.addEventListener("resize", () => zoomBox.classList.contains("show") && placeZoomBox());
//
//     mainImg.addEventListener("load", () => {
//       if (zoomBox.classList.contains("show")) refreshZoomSource();
//     });
//
//     return {
//       async sync() { await refreshZoomSource(); },
//       close() { onLeave(); },
//       isActive() { return zoomBox.classList.contains("show"); },
//     };
//   })();
//
//   // ---------- Gallery thumbs ----------
//   function activateThumb(btn) {
//     if (!btn || !mainImg) return;
//
//     const full = btn.dataset.full || btn.querySelector("img")?.getAttribute("src");
//     const zoomSrc = btn.dataset.zoom || full;
//
//     if (full) {
//       mainImg.src = full;
//       mainImg.dataset.zoomSrc = zoomSrc || full;
//       if (stickyImg) stickyImg.src = full;
//     }
//
//     if (thumbsRoot) {
//       $$(".thumb", thumbsRoot).forEach((t) => {
//         const isActive = t === btn;
//         t.classList.toggle("is-active", isActive);
//         t.setAttribute("aria-pressed", isActive ? "true" : "false");
//       });
//     }
//
//     Zoom.sync();
//   }
//
//   function swapImageForColor(colorId) {
//     if (!colorId) return;
//     let btn = document.querySelector(`.thumb[data-color-id="${colorId}"]`);
//     if (!btn) btn = document.querySelector(".thumb");
//     if (btn) activateThumb(btn);
//   }
//
//   // ---------- Modal Gallery ----------
//   (function initGalleryModal() {
//     const modal = document.getElementById("tlp-gallery-modal");
//     const modalMainImg = document.getElementById("tlp-modal-main-img");
//     const modalThumbs = document.getElementById("tlp-modal-thumbs");
//     if (!modal || !modalMainImg || !modalThumbs) return;
//
//     const dataEl = document.getElementById("tlp-gallery-data");
//     let data = null;
//     try { data = JSON.parse(dataEl?.textContent || "{}"); } catch { data = null; }
//     const images = data?.images || [];
//     let idx = 0;
//     let scrollY = 0;
//
//     function open(atIndex = 0) {
//       idx = Math.max(0, Math.min(atIndex, images.length - 1));
//       render();
//
//       scrollY = window.scrollY || 0;
//       document.body.classList.add("modal-open");
//       document.body.style.top = `-${scrollY}px`;
//
//       modal.classList.add("show");
//       modal.setAttribute("aria-hidden", "false");
//     }
//
//     function close() {
//       modal.classList.remove("show");
//       modal.setAttribute("aria-hidden", "true");
//
//       document.body.classList.remove("modal-open");
//       document.body.style.top = "";
//       window.scrollTo(0, scrollY);
//     }
//
//     function setIndex(i) {
//       if (!images.length) return;
//       idx = (i + images.length) % images.length;
//       render();
//     }
//
//     function render() {
//       const item = images[idx];
//       if (!item) return;
//
//       modalMainImg.src = item.full;
//       modalMainImg.alt = item.alt || "";
//
//       modalThumbs.innerHTML = images.map((it, i) => `
//         <button type="button" class="${i === idx ? "is-active" : ""}" data-i="${i}">
//           <img src="${it.thumb}" alt="${it.alt || ""}" loading="lazy" decoding="async">
//         </button>
//       `).join("");
//
//       // sync main page image
//       mainImg.src = item.full;
//       mainImg.dataset.zoomSrc = item.zoom || item.full;
//       if (stickyImg) stickyImg.src = item.full;
//       Zoom.sync();
//     }
//
//     modal.addEventListener("click", (e) => {
//       const t = e.target;
//       if (t?.dataset?.close === "1") close();
//     });
//
//     modalThumbs.addEventListener("click", (e) => {
//       const btn = e.target.closest("button[data-i]");
//       if (!btn) return;
//       setIndex(Number(btn.dataset.i || 0));
//     });
//
//     modal.querySelector(".tlp-modal-nav.prev")?.addEventListener("click", () => setIndex(idx - 1));
//     modal.querySelector(".tlp-modal-nav.next")?.addEventListener("click", () => setIndex(idx + 1));
//
//     document.addEventListener("keydown", (e) => {
//       if (!modal.classList.contains("show")) return;
//       if (e.key === "Escape") close();
//       if (e.key === "ArrowLeft") setIndex(idx + 1);   // RTL حس بهتر
//       if (e.key === "ArrowRight") setIndex(idx - 1);
//     });
//
//     window.__tlpOpenGalleryModal = open;
//   })();
//
//   // ---------- Selection state ----------
//   let selectedColorId = colorWrap?.querySelector(".active")?.dataset?.colorId || null;
//   let selectedSizeId = sizeSelect && sizeSelect.value && sizeSelect.value !== "#" ? sizeSelect.value : null;
//
//   let userInteracted = false; // برای جلوگیری از دست زدن به قیمت سرور در init
//
//   async function onSelectionChange({ fromUser = false } = {}) {
//     if (fromUser) userInteracted = true;
//
//     if (!selectedColorId) {
//       const first = colorWrap?.querySelector("a[data-color-id]")?.getAttribute("data-color-id");
//       if (first) selectedColorId = first;
//     }
//
//     if (selectedColorId && isSizeRequired(selectedColorId) && !selectedSizeId) {
//       enableAdd(false);
//       if (hiddenVid) hiddenVid.value = "";
//       swapImageForColor(selectedColorId);
//       return;
//     }
//
//     const cell = resolveVariantCell(selectedColorId, selectedSizeId);
//     const variantId = resolveVariantId(selectedColorId, selectedSizeId);
//
//     if (hiddenVid) hiddenVid.value = variantId ? String(variantId) : "";
//
//     if (selectedColorId) swapImageForColor(selectedColorId);
//
//     const stock = Number(cell?.stock ?? (variantId ? vprices?.[variantId]?.stock : 0) ?? 0);
//     updateLowStock(stock);
//     enableAdd(!!(variantId && stock > 0));
//
//     if (!variantId) return;
//
//     // اگر کاربر هنوز هیچ تعاملی نکرده، قیمت سرور رو دست نزن (فقط add/stock رو هندل کن)
//     if (!userInteracted) return;
//
//     optimisticUpdate(variantId, cell);
//     fetchAndFix(variantId);
//   }
//
//   // ---------- Events ----------
//   if (colorWrap) {
//     $$("#color-swatches a[data-color-id]").forEach((a) => {
//       if (!a.dataset.colorId) a.dataset.colorId = a.getAttribute("data-color-id") || "";
//       a.addEventListener("click", (ev) => {
//         ev.preventDefault();
//         userInteracted = true;
//         $$("#color-swatches a").forEach((x) => x.classList.remove("active"));
//         a.classList.add("active");
//         selectedColorId = a.dataset.colorId || null;
//
//         if (!isSizeRequired(selectedColorId)) selectedSizeId = null;
//
//         onSelectionChange({ fromUser: true });
//       });
//     });
//   }
//
//   if (sizeSelect) {
//     sizeSelect.addEventListener("change", () => {
//       userInteracted = true;
//       const v = sizeSelect.value;
//       selectedSizeId = v && v !== "#" ? v : null;
//       onSelectionChange({ fromUser: true });
//     });
//   }
//
//   if (thumbsRoot) {
//     const canHoverThumbs = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
//     let hoverTimer = null;
//
//     $$(".thumb", thumbsRoot).forEach((btn) => {
//       btn.addEventListener("click", (e) => {
//         e.preventDefault();
//
//         // اگر overlay +X دارد → مودال
//         if (btn.querySelector(".thumb-more")) {
//           const activeIndex = Number(btn.dataset.index || 0);
//           window.__tlpOpenGalleryModal?.(activeIndex);
//           return;
//         }
//
//         activateThumb(btn);
//       });
//
//       if (canHoverThumbs) {
//         btn.addEventListener("mouseenter", () => {
//           clearTimeout(hoverTimer);
//           hoverTimer = setTimeout(() => {
//             if (!btn.classList.contains("is-active")) activateThumb(btn);
//           }, 60);
//         });
//         btn.addEventListener("mouseleave", () => clearTimeout(hoverTimer));
//       }
//     });
//   }
//
//   // ---------- Form submit ----------
//   if (form) {
//     form.addEventListener("submit", (e) => {
//       if (qtyInput) {
//         const min = Number(qtyInput.min || 1);
//         const max = Number(qtyInput.max || 99);
//         const v = Number(qtyInput.value || 1);
//         qtyInput.value = String(Math.min(Math.max(v, min), max));
//       }
//
//       const vid = hiddenVid?.value || "";
//       const sizeNeeded = selectedColorId && isSizeRequired(selectedColorId);
//       if (!vid || (sizeNeeded && !selectedSizeId)) {
//         e.preventDefault();
//         alert(sizeNeeded && !selectedSizeId ? "لطفاً سایز را انتخاب کنید." : "لطفاً یک واریانت معتبر انتخاب کنید.");
//         enableAdd(false);
//         return false;
//       }
//     });
//   }
//
//   // ---------- Initial run ----------
//   // در init فقط وضعیت واریانت/stock رو تنظیم می‌کنیم، قیمت سرور رو دست نمی‌زنیم
//   onSelectionChange({ fromUser: false });
// })();
//
// // static/js/product.js
// (function () {
//   "use strict";
//
//   function postFormUrlencoded(url, dataObj, csrf) {
//     const body = new URLSearchParams(dataObj).toString();
//     return fetch(url, {
//       method: "POST",
//       headers: {
//         "X-CSRFToken": csrf || "",
//         "X-Requested-With": "XMLHttpRequest",
//         "Content-Type": "application/x-www-form-urlencoded",
//       },
//       body,
//     });
//   }
//
//   function initRating() {
//     const containers = document.querySelectorAll(".stars");
//     if (!containers.length) return;
//
//     containers.forEach((container) => {
//       const stars = Array.from(container.querySelectorAll("i"));
//       if (!stars.length) return;
//
//       const objectId = container.dataset.objectId;
//       const contentTypeId = container.dataset.contentTypeId;
//       const rateUrl = container.dataset.rateUrl;
//       const getUrl = container.dataset.getUrl;
//       const csrf = container.dataset.csrf;
//
//       let userHasRated = false;
//
//       function paint(score) {
//         stars.forEach((s, idx) => {
//           s.classList.remove("bi-star-fill", "hovered");
//           // اگر از bi-star استفاده می‌کنی بهتره کلاس outline هم ست بشه
//           // (اختیاری) s.classList.add("bi-star");
//           if (idx < score) s.classList.add("bi-star-fill");
//         });
//       }
//
//       // Hover effect
//       stars.forEach((star, index) => {
//         star.addEventListener("mouseenter", () => {
//           if (userHasRated) return;
//           stars.forEach((s, i) => s.classList.toggle("hovered", i <= index));
//         });
//         star.addEventListener("mouseleave", () => {
//           if (userHasRated) return;
//           stars.forEach((s) => s.classList.remove("hovered"));
//         });
//       });
//
//       // Click
//       stars.forEach((star) => {
//         star.addEventListener("click", () => {
//           if (userHasRated) return;
//
//           const score = parseInt(star.dataset.score || "0", 10);
//           if (!score || !rateUrl) return;
//
//           postFormUrlencoded(
//             rateUrl,
//             { object_id: objectId, content_type_id: contentTypeId, score: score },
//             csrf
//           )
//             .then((res) => res.json())
//             .then((data) => {
//               if (data.status === "success") {
//                 userHasRated = true;
//                 paint(parseInt(data.user_score || "0", 10));
//
//                 const wrap = container.parentElement || document;
//                 const avg = wrap.querySelector(".rating-average");
//                 const cnt = wrap.querySelector(".rating-count");
//                 if (avg) avg.textContent = data.average;
//                 if (cnt) cnt.textContent = `(${data.count} رأی)`;
//
//                 stars.forEach((s) => (s.style.pointerEvents = "none"));
//               } else {
//                 alert(data.message || "خطایی رخ داد.");
//               }
//             })
//             .catch(() => alert("خطا در ارتباط با سرور."));
//         });
//       });
//
//       // Initial fetch: user rating
//       if (getUrl) {
//         const url = `${getUrl}?object_id=${encodeURIComponent(objectId)}&content_type_id=${encodeURIComponent(contentTypeId)}`;
//         fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
//           .then((res) => res.json())
//           .then((data) => {
//             const us = parseInt(data.user_score || "0", 10);
//             if (us) {
//               userHasRated = true;
//               paint(us);
//               stars.forEach((s) => (s.style.pointerEvents = "none"));
//             } else {
//               paint(0);
//             }
//           })
//           .catch(() => {
//             // silent
//           });
//       }
//     });
//   }
//
//   function initPriceChart() {
//     const canvas = document.getElementById("priceLineChart");
//     if (!canvas) return;
//
//     const dataScript = document.getElementById("price-history-data");
//     if (!dataScript) return;
//
//     let payload = null;
//     try {
//       payload = JSON.parse(dataScript.textContent || "{}");
//     } catch (e) {
//       return;
//     }
//
//     const labels = payload.labels || [];
//     const prices = payload.prices || [];
//
//     if (!labels.length || !prices.length || typeof Chart === "undefined") return;
//
//     const ctx = canvas.getContext("2d");
//
//     // اگر قبلاً چارت ساخته شده بود (ناوبری PJAX/AJAX)، پاکش کن
//     if (canvas._chartInstance) {
//       try { canvas._chartInstance.destroy(); } catch (e) {}
//     }
//
//     canvas._chartInstance = new Chart(ctx, {
//       type: "line",
//       data: {
//         labels: labels,
//         datasets: [
//           {
//             label: "قیمت",
//             data: prices,
//             tension: 0.35,
//             fill: false,
//           },
//         ],
//       },
//       options: {
//         responsive: true,
//         maintainAspectRatio: false,
//         interaction: { mode: "index", intersect: false },
//         plugins: {
//           legend: { display: false },
//           tooltip: {
//             callbacks: {
//               label: function (ctx) {
//                 const v = ctx.parsed.y;
//                 try {
//                   return `${v.toLocaleString("fa-IR")} تومان`;
//                 } catch (e) {
//                   return `${v} تومان`;
//                 }
//               },
//             },
//           },
//         },
//         scales: {
//           y: {
//             ticks: {
//               callback: function (value) {
//                 try {
//                   return Number(value).toLocaleString("fa-IR");
//                 } catch (e) {
//                   return value;
//                 }
//               },
//             },
//           },
//         },
//       },
//     });
//   }
//
//   document.addEventListener("DOMContentLoaded", function () {
//     initRating();
//     initPriceChart();
//   });
// })();


// // ================== Price History Chart (Chart.js) ==================
// (function () {
//   "use strict";
//
//   function initPriceChart() {
//     const jsonScript = document.getElementById("price-chart-data");
//     const canvas = document.getElementById("priceLineChart");
//     const card = document.querySelector("#line-chart");
//
//     if (!jsonScript || !canvas) return;
//     if (typeof Chart === "undefined") return;
//
//     let chartData;
//     try {
//       chartData = JSON.parse(jsonScript.textContent || "{}");
//     } catch (e) {
//       console.error("price-chart-data JSON parse error", e);
//       return;
//     }
//
//     const labelsRaw = chartData.labels || [];
//     const minPrices = chartData.min_prices || [];
//     const avgPrices = chartData.avg_prices || [];
//
//     // اگر دیتایی نیست
//     if (!labelsRaw.length || (!minPrices.length && !avgPrices.length)) {
//       if (card) {
//         card.innerHTML =
//           '<div class="p-3 text-muted" style="font-size:0.9rem;">برای این محصول هنوز سابقهٔ قیمت ثبت نشده است.</div>';
//       }
//       return;
//     }
//
//     // تبدیل تاریخ‌ها به شمسی (fa-IR)
//     const labels = labelsRaw.map((d) => {
//       try {
//         const dt = new Date(d);
//         return dt.toLocaleDateString("fa-IR");
//       } catch {
//         return d;
//       }
//     });
//
//     // رنگ‌ها از CSS Variables (اگر داری) - fallback هم گذاشتم
//     const rootStyles = getComputedStyle(document.documentElement);
//     const colorMin =
//       rootStyles.getPropertyValue("--chart-min").trim() ||
//       rootStyles.getPropertyValue("--line").trim() ||
//       "#2563eb";
//     const colorAvg = rootStyles.getPropertyValue("--chart-avg").trim() || "#22c55e";
//     const gridColor = rootStyles.getPropertyValue("--grid").trim() || "#eff3f8";
//     const axisColor = rootStyles.getPropertyValue("--axis-muted").trim() || "#9ca3af";
//     const fillBg = rootStyles.getPropertyValue("--chart-fill").trim() || "rgba(250,106,53,0.08)";
//
//     const meta = chartData.meta || {};
//     const minY = meta.min_y ?? meta.min_overall;
//     const maxY = meta.max_y ?? meta.max_overall;
//
//     const ctx = canvas.getContext("2d");
//
//     // اگر قبلاً ساختیم، نابودش کن (برای جلوگیری از چندبار رندر)
//     if (canvas._priceChartInstance) {
//       canvas._priceChartInstance.destroy();
//       canvas._priceChartInstance = null;
//     }
//
//     // دیتاست‌ها
//     const datasets = [];
//     if (minPrices.length) {
//       datasets.push({
//         label: "کمترین قیمت",
//         data: minPrices,
//         borderColor: colorMin,
//         backgroundColor: colorMin,
//         pointBackgroundColor: colorMin,
//         pointRadius: 3,
//         pointHoverRadius: 4,
//         borderWidth: 2,
//         tension: 0.3,
//       });
//     }
//     if (avgPrices.length) {
//       datasets.push({
//         label: "میانگین قیمت",
//         data: avgPrices,
//         borderColor: colorAvg,
//         backgroundColor: fillBg,
//         pointBackgroundColor: colorAvg,
//         pointRadius: 3,
//         pointHoverRadius: 4,
//         borderWidth: 2,
//         tension: 0.3,
//         fill: "origin",
//       });
//     }
//
//     const chart = new Chart(ctx, {
//       type: "line",
//       data: { labels, datasets },
//       options: {
//         responsive: true,
//         maintainAspectRatio: false,
//         plugins: {
//           legend: {
//             display: true,
//             labels: { usePointStyle: true, boxWidth: 8, boxHeight: 8 },
//           },
//           tooltip: {
//             callbacks: {
//               label: function (ctx) {
//                 const val = ctx.parsed.y || 0;
//                 const title = ctx.dataset.label || "";
//                 return `${title}: ${val.toLocaleString("fa-IR")} تومان`;
//               },
//             },
//           },
//         },
//         scales: {
//           x: {
//             grid: { display: false },
//             ticks: {
//               color: axisColor,
//               maxRotation: 0,
//               autoSkip: true,
//               maxTicksLimit: 6,
//             },
//           },
//           y: {
//             grid: { color: gridColor },
//             ticks: {
//               color: axisColor,
//               callback: function (value) {
//                 return Number(value || 0).toLocaleString("fa-IR");
//               },
//             },
//             min: typeof minY === "number" ? minY : undefined,
//             max: typeof maxY === "number" ? maxY : undefined,
//           },
//         },
//       },
//     });
//
//     canvas._priceChartInstance = chart;
//   }
//
//   // اگر Chart با defer دیرتر لود شد، یک ریتری سبک می‌زنیم
//   function boot() {
//     if (typeof Chart !== "undefined") {
//       initPriceChart();
//       return;
//     }
//     let tries = 0;
//     const t = setInterval(() => {
//       tries += 1;
//       if (typeof Chart !== "undefined") {
//         clearInterval(t);
//         initPriceChart();
//       } else if (tries >= 30) {
//         clearInterval(t);
//       }
//     }, 100);
//   }
//
//   document.addEventListener("DOMContentLoaded", boot);
// })();
//
// // ======================= Rating (Stars) =======================
// (function () {
//   "use strict";
//
//   const getCSRFToken = () => {
//     // 1) از meta
//     const meta = document.querySelector('meta[name="csrf-token"]');
//     if (meta?.content) return meta.content;
//
//     // 2) از cookie (Django default: csrftoken)
//     const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
//     return m ? decodeURIComponent(m[1]) : "";
//   };
//
//   function initRatings() {
//     const containers = document.querySelectorAll(".stars");
//     if (!containers.length) return;
//
//     const csrf = getCSRFToken();
//
//     containers.forEach((container) => {
//       const stars = Array.from(container.querySelectorAll("i"));
//       if (!stars.length) return;
//
//       const objectId = container.dataset.objectId;
//       const contentTypeId = container.dataset.contentTypeId;
//       const addUrl = container.dataset.addUrl;
//       const userUrl = container.dataset.userUrl;
//
//       if (!objectId || !contentTypeId || !addUrl || !userUrl) return;
//
//       let userHasRated = false;
//
//       const fillStars = (score) => {
//         stars.forEach((s, idx) => {
//           s.classList.toggle("bi-star-fill", idx < score);
//           s.classList.remove("hovered");
//         });
//       };
//
//       const lock = () => {
//         stars.forEach((s) => (s.style.pointerEvents = "none"));
//       };
//
//       // Hover preview فقط وقتی رأی نداده
//       stars.forEach((star, index) => {
//         star.addEventListener("mouseenter", () => {
//           if (userHasRated) return;
//           stars.forEach((s, i) => s.classList.toggle("hovered", i <= index));
//         });
//         star.addEventListener("mouseleave", () => {
//           if (userHasRated) return;
//           stars.forEach((s) => s.classList.remove("hovered"));
//         });
//       });
//
//       // Click submit
//       stars.forEach((star) => {
//         star.addEventListener("click", async () => {
//           if (userHasRated) return;
//
//           const score = parseInt(star.dataset.score || "0", 10);
//           if (!score) return;
//
//           try {
//             const body = new URLSearchParams({
//               object_id: String(objectId),
//               content_type_id: String(contentTypeId),
//               score: String(score),
//             });
//
//             const res = await fetch(addUrl, {
//               method: "POST",
//               headers: {
//                 "X-CSRFToken": csrf,
//                 "X-Requested-With": "XMLHttpRequest",
//                 "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
//               },
//               body,
//             });
//
//             const data = await res.json();
//
//             if (data.status === "success") {
//               userHasRated = true;
//
//               fillStars(Number(data.user_score || 0));
//
//               const avg = container.parentElement?.querySelector(".rating-average");
//               const cnt = container.parentElement?.querySelector(".rating-count");
//               if (avg) avg.textContent = data.average;
//               if (cnt) cnt.textContent = `(${data.count} رأی)`;
//
//               lock();
//             } else {
//               alert(data.message || "خطایی رخ داد.");
//             }
//           } catch (e) {
//             console.error("Rating submit error:", e);
//             alert("خطا در ارتباط با سرور.");
//           }
//         });
//       });
//
//       // Load user rating on refresh
//       (async () => {
//         try {
//           const url = new URL(userUrl, window.location.origin);
//           url.searchParams.set("object_id", String(objectId));
//           url.searchParams.set("content_type_id", String(contentTypeId));
//
//           const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
//           const data = await res.json();
//
//           if (data.user_score) {
//             userHasRated = true;
//             fillStars(Number(data.user_score || 0));
//             lock();
//           } else {
//             fillStars(0);
//           }
//         } catch (e) {
//           console.error("Rating load error:", e);
//         }
//       })();
//     });
//   }
//
//   document.addEventListener("DOMContentLoaded", initRatings);
// })();


/* ======================= PRODUCT: Variant resolution + live pricing + gallery + zoom + wishlist + chart ======================= */
(function () {
    "use strict";

    // ---------- Shorthands ----------
    const $ = (sel, root = document) => root.querySelector(sel);
    const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

    // ---------- Elements ----------
    const form = $("#add-to-cart-form");
    const hiddenVid = $("#variant_id");
    const btnAdd = $("#btn-add");
    const qtyInput = $("#qty");
    const colorWrap = $("#color-swatches");
    const sizeSelect = $("#size");
    const outBadge = $("#out-badge");


    // Gallery
    const stage = $("#tlp-stage") || $(".tlp-gallery .stage");
    const mainImg = $("#tlp-main");
    const stickyImg = $("#sticky-img");
    const thumbsRoot = $(".thumbs");

    // Price/discount UI
    const elPriceNum = $("#price-num");
    const elCompareNum = $("#compare-num");
    const elSaveBox = $("#price-save");
    const elOffBadge = $("#off-badge");
    const elOffAmount = $("#off-amount");
    const lowStockEl = $(".low-stock");

    // optional API endpoint (for precise pricing after optimistic update)
    const priceApi = $("#price-api")?.dataset?.url || null;

    // ---------- Helpers ----------
    const intcomma = (n) => (Number.isFinite(n) ? n.toLocaleString("fa-IR") : "");
    const clamp = (x, a, b) => Math.min(Math.max(x, a), b);


    function setOutOfStockUI(isOut) {
        if (outBadge) outBadge.style.display = isOut ? "" : "none";
        enableAdd(!isOut); // دکمه هم sync میشه
    }

    function computeTotalStockFromVprices() {
        try {
            return Object.values(vprices || {}).reduce((sum, row) => sum + Number(row?.stock || 0), 0);
        } catch {
            return 0;
        }
    }


    function readJSON(id) {
        const el = document.getElementById(id);
        if (!el) return null;
        try {
            return JSON.parse(el.textContent || el.innerText || "null");
        } catch {
            return null;
        }
    }

    // ---------- Data from template (JSON tags) ----------
    // variant-matrix: { matrix: { "<color_id>": { "<size_id|OS>": { price, stock, sku, compare_at?, variant_id? } } }, sizes: {...} }
    // variant-prices: { "<variant_id>": { price, stock, sku, compare_at? } }
    const matrixObj = readJSON("variant-matrix") || {};
    const vprices = readJSON("variant-prices") || {};
    const M = matrixObj.matrix || {};
    const SIZES_META = matrixObj.sizes || {}; // unused here but kept

    // ---------- Variant resolution ----------
    function isSizeRequired(colorId) {
        const row = M[String(colorId)] || {};
        const keys = Object.keys(row || {});
        if (!keys.length) return false;
        return !(keys.length === 1 && keys[0] === "OS");
    }

    function resolveVariantCell(colorId, sizeId) {
        if (!colorId) return null;
        const row = M[String(colorId)] || {};
        const key = sizeId || (row["OS"] ? "OS" : Object.keys(row)[0]);
        if (!key) return null;
        return row[String(key)] || null;
    }

    function resolveVariantId(colorId, sizeId) {
        const cell = resolveVariantCell(colorId, sizeId);
        if (!cell) return null;

        if (cell.variant_id) return String(cell.variant_id);

        // fallback by sku match
        if (cell.sku) {
            const matches = Object.entries(vprices).filter(([, v]) => (v && v.sku) === cell.sku);
            if (matches.length === 1) return String(matches[0][0]);
        }
        return null;
    }

    // ---------- Price UI ----------
    function setPriceUI({finalPrice, basePrice, discountPercent, discountAmount}) {
        finalPrice = Number(finalPrice || 0);
        basePrice = basePrice === null || basePrice === undefined ? null : Number(basePrice);

        if (elPriceNum) elPriceNum.textContent = intcomma(finalPrice || 0);

        if (!elSaveBox || !elCompareNum || !elOffBadge || !elOffAmount) return;

        const hasDiscount = !!(basePrice && finalPrice && finalPrice < basePrice);

        if (hasDiscount) {
            elCompareNum.textContent = intcomma(basePrice);
            elOffBadge.textContent = `${Math.round(discountPercent || 0)}٪ تخفیف`;
            elOffAmount.textContent = discountAmount
                ? `مبلغ کسرشده: ${intcomma(discountAmount)} تومان`
                : "";
            elSaveBox.style.display = "";
        } else {
            elSaveBox.style.display = "none";
            elCompareNum.textContent = "";
            elOffBadge.textContent = "";
            elOffAmount.textContent = "";
        }
    }


    function optimisticUpdate(variantId, cell) {
        const cached = vprices[String(variantId)] || cell || {};
        const finalPrice = Number(cached.price ?? 0);
        const basePrice = Number(cached.compare_at ?? 0);

        const hasDisc = basePrice && finalPrice && finalPrice < basePrice;
        const discountAmount = hasDisc ? basePrice - finalPrice : 0;
        const discountPercent = hasDisc ? (discountAmount / basePrice) * 100 : 0;
        console.log("cached:", cached);
        console.log("price/compare_at:", cached.price, cached.compare_at);
        console.log("final/base:", finalPrice, basePrice);
        console.log("variantId:", variantId, "cell:", cell);
        document.getElementById("variant-prices")?.textContent?.slice(0, 600)
        setPriceUI({
            finalPrice,
            basePrice: hasDisc ? basePrice : null,
            discountPercent: hasDisc ? discountPercent : null,
            discountAmount: hasDisc ? discountAmount : null,
        });
    }

    async function fetchAndFix(variantId) {
        if (!priceApi || !variantId) return;
        try {
            const url = new URL(priceApi, window.location.origin);
            url.searchParams.set("variant", String(variantId));
            const res = await fetch(url, {headers: {"X-Requested-With": "XMLHttpRequest"}});
            if (!res.ok) return;
            const data = await res.json();
            if (!data || data.ok === false) return;

            setPriceUI({
                finalPrice: Number(data.price_final ?? 0),
                basePrice: data.price_base ?? null,
                discountPercent: data.discount_percent ?? null,
                discountAmount: data.discount_amount ?? null,
            });
        } catch (_e) {
            // silent fallback to optimistic
        }
    }

    function updateLowStock(stock) {
        if (!lowStockEl) return;
        if (stock > 0 && stock <= 5) {
            lowStockEl.style.display = "";
            lowStockEl.textContent = "تنها " + intcomma(stock) + " عدد در انبار باقی مانده";
        } else {
            lowStockEl.style.display = "none";
        }
    }

    function enableAdd(enabled) {
        if (!btnAdd) return;
        btnAdd.disabled = !enabled;
        btnAdd.classList.toggle("is-disabled", !enabled);
        btnAdd.setAttribute("aria-disabled", (!enabled).toString());
    }

    // ---------- Zoom (Walmart-like hover) ----------
    const Zoom = (function () {
        const zoomBox = $("#tlp-zoom-box");
        const zoomImg = $("#tlp-zoom-img");
        const lens = stage ? $(".zoom-lens", stage) : null;

        if (!stage || !mainImg || !lens || !zoomBox || !zoomImg) {
            return {
                sync() {
                }, close() {
                }, isActive() {
                    return false;
                }
            };
        }

        // disable on touch/mobile
        const canHover = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
        if (!canHover) {
            return {
                sync() {
                }, close() {
                }, isActive() {
                    return false;
                }
            };
        }

        // natural size of zoom image
        let natW = 0, natH = 0;

        function getZoomSrc() {
            // ⭐️ اگر dataset.zoomSrc ست شده باشد، از آن استفاده می‌کنیم (بهتر/شارپ‌تر)
            return mainImg.dataset.zoomSrc || mainImg.currentSrc || mainImg.src;
        }

        function preloadNatural(src) {
            return new Promise((resolve) => {
                const im = new Image();
                im.onload = () => resolve({w: im.naturalWidth || 0, h: im.naturalHeight || 0});
                im.onerror = () => resolve({w: 0, h: 0});
                im.src = src;
            });
        }

        async function refreshZoomSource() {
            const src = getZoomSrc();
            const nat = await preloadNatural(src);
            natW = nat.w;
            natH = nat.h;
            zoomImg.style.backgroundImage = `url("${src}")`;
        }

        function placeZoomBox() {
            const r = stage.getBoundingClientRect();
            const gap = 14;

            const boxW = zoomBox.offsetWidth || 420;
            const boxH = zoomBox.offsetHeight || 420;

            // RTL preference: left side
            let left = r.left - gap - boxW;
            if (left < 8) left = r.right + gap;

            let top = r.top;
            const maxTop = window.innerHeight - boxH - 8;
            if (top > maxTop) top = Math.max(8, maxTop);

            zoomBox.style.left = `${left}px`;
            zoomBox.style.top = `${top}px`;
        }

        function clamp2(v, min, max) {
            return Math.max(min, Math.min(max, v));
        }

        function update(e) {
            const imgRect = mainImg.getBoundingClientRect();
            const x = e.clientX - imgRect.left;
            const y = e.clientY - imgRect.top;
            if (x < 0 || y < 0 || x > imgRect.width || y > imgRect.height) return;

            // Lens size
            const lensW = Math.max(90, imgRect.width * 0.35);
            const lensH = Math.max(90, imgRect.height * 0.35);
            lens.style.width = `${lensW}px`;
            lens.style.height = `${lensH}px`;

            const lensLeft = clamp2(x - lensW / 2, 0, imgRect.width - lensW);
            const lensTop = clamp2(y - lensH / 2, 0, imgRect.height - lensH);

            // Lens translate in stage coords
            const stageRect = stage.getBoundingClientRect();
            const leftOnStage = (imgRect.left - stageRect.left) + lensLeft;
            const topOnStage = (imgRect.top - stageRect.top) + lensTop;
            lens.style.transform = `translate(${leftOnStage}px, ${topOnStage}px)`;

            // % position (center of lens)
            const px = (lensLeft + lensW / 2) / imgRect.width;
            const py = (lensTop + lensH / 2) / imgRect.height;

            // ⭐️ شارپ: background-size بر اساس رزولوشن طبیعی تصویر زوم
            // اگر natW/natH نبود، fallback به نسخه قبلی
            const bgW = natW || (imgRect.width * 3);
            const bgH = natH || (imgRect.height * 3);
            zoomImg.style.backgroundSize = `${bgW}px ${bgH}px`;

            // ⭐️ شارپ: background-position بر اساس پیکسل واقعی
            // مرکز انتخاب شده باید وسط zoom-box قرار بگیرد
            const boxW = zoomBox.clientWidth || 420;
            const boxH = zoomBox.clientHeight || 420;

            const cx = px * bgW;
            const cy = py * bgH;

            const bgLeft = clamp2(cx - boxW / 2, 0, Math.max(0, bgW - boxW));
            const bgTop = clamp2(cy - boxH / 2, 0, Math.max(0, bgH - boxH));

            zoomImg.style.backgroundPosition = `-${bgLeft}px -${bgTop}px`;
        }

        async function onEnter() {
            await refreshZoomSource();
            stage.classList.add("zooming");
            zoomBox.classList.add("show");
            placeZoomBox();
        }

        function onLeave() {
            stage.classList.remove("zooming");
            zoomBox.classList.remove("show");
        }

        stage.addEventListener("mouseenter", onEnter);
        stage.addEventListener("mousemove", update);
        stage.addEventListener("mouseleave", onLeave);

        window.addEventListener("scroll", () => zoomBox.classList.contains("show") && placeZoomBox(), {passive: true});
        window.addEventListener("resize", () => zoomBox.classList.contains("show") && placeZoomBox());

        // اگر src عوض شد و زوم باز بود، طبیعی‌اش را دوباره بگیر
        mainImg.addEventListener("load", () => {
            if (zoomBox.classList.contains("show")) refreshZoomSource();
        });

        return {
            async sync() {
                await refreshZoomSource();
            },
            close() {
                onLeave();
            },
            isActive() {
                return zoomBox.classList.contains("show");
            },
        };
    })();

    // ---------- Gallery thumbs ----------
    function activateThumb(btn) {
        if (!btn || !mainImg) return;

        const full = btn.dataset.full || btn.querySelector("img")?.getAttribute("src");
        const zoomSrc = btn.dataset.zoom || full;     // ⭐️ مهم

        if (full) {
            mainImg.src = full;
            mainImg.dataset.zoomSrc = zoomSrc || full;  // ⭐️ مهم (همین مشکل توست)
            if (stickyImg) stickyImg.src = full;
        }

        $$(".thumb", thumbsRoot || document).forEach((t) => {
            const isActive = t === btn;
            t.classList.toggle("is-active", isActive);
            t.setAttribute("aria-pressed", isActive ? "true" : "false");
        });

        // ریست پوزیشن (اختیاری)
        const zb = document.getElementById("tlp-zoom-box");
        if (zb?.classList.contains("show") && zoomImg) {
            zoomImg.style.backgroundPosition = "50% 50%";
        }

        Zoom.sync(); // دیگه لازم نیست catch خالی بذاری
    }

// allow modal to update main image (without needing real thumb button)
    window.__tlpSetMainFromModal = function (item) {
        if (!item || !mainImg) return;
        mainImg.src = item.full;
        mainImg.dataset.zoomSrc = item.zoom || item.full;
        if (stickyImg) stickyImg.src = item.full;
        Zoom.sync();
    };

    function swapImageForColor(colorId) {
        if (!colorId) return;
        let btn = document.querySelector(`.thumb[data-color-id="${colorId}"]`);
        if (!btn) btn = document.querySelector(".thumb");
        if (btn) activateThumb(btn);
    }

    // ---------- State ----------
    let selectedColorId = colorWrap?.querySelector(".active")?.dataset?.colorId || null;
    let selectedSizeId = sizeSelect && sizeSelect.value && sizeSelect.value !== "#" ? sizeSelect.value : null;

    // ---------- Main selection handler ----------
async function onSelectionChange() {
  if (!selectedColorId) {
    const first = colorWrap?.querySelector("a[data-color-id]")?.getAttribute("data-color-id");
    if (first) selectedColorId = first;
  }

  // size required but not selected
  if (selectedColorId && isSizeRequired(selectedColorId) && !selectedSizeId) {
    if (hiddenVid) hiddenVid.value = "";
    swapImageForColor(selectedColorId);

    updateLowStock(0);
    setOutOfStockUI(true);   // ✅ این همون چیزیه که کم داشتی
    return;
  }

  const cell = resolveVariantCell(selectedColorId, selectedSizeId);
  const variantId = resolveVariantId(selectedColorId, selectedSizeId);

  if (hiddenVid) hiddenVid.value = variantId ? String(variantId) : "";

  if (selectedColorId) swapImageForColor(selectedColorId);

  // ---- STOCK RESOLUTION (color/size aware + fallback) ----
  let stock = 0;

  if (cell && cell.stock !== undefined && cell.stock !== null) {
    stock = Number(cell.stock || 0);
  } else if (variantId && vprices?.[String(variantId)]?.stock !== undefined) {
    stock = Number(vprices[String(variantId)]?.stock || 0);
  } else {
    stock = computeTotalStockFromVprices();
  }

  updateLowStock(stock);

  const hasAnyVariants = vprices && Object.keys(vprices).length > 0;
  const outOfStock = hasAnyVariants ? (stock <= 0 || !variantId) : true;

  setOutOfStockUI(outOfStock); // ✅ badge + button sync

  if (variantId) {
    optimisticUpdate(variantId, cell);
    fetchAndFix(variantId);
  }
}



    // async function onSelectionChange() {
    //     if (!selectedColorId) {
    //         const first = colorWrap?.querySelector("a[data-color-id]")?.getAttribute("data-color-id");
    //         if (first) selectedColorId = first;
    //     }
    //
    //     // size required but not selected
    //     if (selectedColorId && isSizeRequired(selectedColorId) && !selectedSizeId) {
    //         enableAdd(false);
    //         if (hiddenVid) hiddenVid.value = "";
    //         // still swap to color image
    //         swapImageForColor(selectedColorId);
    //         return;
    //     }
    //
    //     const cell = resolveVariantCell(selectedColorId, selectedSizeId);
    //     const variantId = resolveVariantId(selectedColorId, selectedSizeId);
    //
    //     if (hiddenVid) hiddenVid.value = variantId ? String(variantId) : "";
    //
    //     if (selectedColorId) swapImageForColor(selectedColorId);
    //
    //     const stock = Number(cell?.stock ?? vprices?.[variantId]?.stock ?? 0);
    //     updateLowStock(stock);
    //     enableAdd(!!(variantId && stock > 0));
    //
    //     if (variantId) {
    //         optimisticUpdate(variantId, cell);
    //         fetchAndFix(variantId);
    //     }
    // }

    // ---------- Events ----------
    // Colors
    if (colorWrap) {
        $$("#color-swatches a[data-color-id]").forEach((a) => {
            if (!a.dataset.colorId) a.dataset.colorId = a.getAttribute("data-color-id") || "";
            a.addEventListener("click", (ev) => {
                ev.preventDefault();
                $$("#color-swatches a").forEach((x) => x.classList.remove("active"));
                a.classList.add("active");
                selectedColorId = a.dataset.colorId || null;

                // If size not needed for this color, clear size selection
                if (!isSizeRequired(selectedColorId)) selectedSizeId = null;

                onSelectionChange();
            });
        });
    }

    // Size
    if (sizeSelect) {
        sizeSelect.addEventListener("change", () => {
            const v = sizeSelect.value;
            selectedSizeId = v && v !== "#" ? v : null;
            onSelectionChange();
        });
    }
    // حالتی ک با موس هاور روی تامب عکس اصلی  میشه
    if (thumbsRoot) {
        const canHoverThumbs = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
        let hoverTimer = null;

        $$(".thumb", thumbsRoot).forEach((btn) => {
            // کلیک همیشه فعال
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                activateThumb(btn);
            });

            btn.addEventListener("click", (e) => {
                e.preventDefault();

                // اگر این تامب overlay +X دارد → مودال را باز کن
                if (btn.querySelector(".thumb-more")) {
                    const activeIndex = Number(btn.dataset.index || 0); // یا 4
                    window.__tlpOpenGalleryModal?.(activeIndex);
                    return;
                }

                activateThumb(btn);
            });
            // هاور فقط روی دسکتاپ
            if (canHoverThumbs) {
                btn.addEventListener("mouseenter", () => {
                    clearTimeout(hoverTimer);
                    hoverTimer = setTimeout(() => {
                        if (!btn.classList.contains("is-active")) {
                            activateThumb(btn);
                        }
                    }, 60); // اگر خواستی سریع‌تر: 0-30، نرم‌تر: 80-120
                });

                btn.addEventListener("mouseleave", () => {
                    clearTimeout(hoverTimer);
                });
            }
        });
    }

// ---------- Modal Gallery ----------
    (function initGalleryModal() {
        const modal = document.getElementById("tlp-gallery-modal");
        const modalMainImg = document.getElementById("tlp-modal-main-img");
        const modalThumbs = document.getElementById("tlp-modal-thumbs");
        if (!modal || !modalMainImg || !modalThumbs) return;

        const dataEl = document.getElementById("tlp-gallery-data");
        let data = null;
        try {
            data = JSON.parse(dataEl?.textContent || "{}");
        } catch {
            data = null;
        }
        const images = data?.images || [];

        let idx = 0;

        let __scrollY = 0;

        function lockBodyScroll() {
            __scrollY = window.scrollY || 0;
            document.body.classList.add("modal-open");
            document.body.style.top = `-${__scrollY}px`;
            document.body.style.left = "0";
            document.body.style.right = "0";
            document.body.style.width = "100%";
        }

        function unlockBodyScroll() {
            document.body.classList.remove("modal-open");
            const y = __scrollY;
            document.body.style.top = "";
            document.body.style.left = "";
            document.body.style.right = "";
            document.body.style.width = "";
            window.scrollTo(0, y);
        }

        //

        function open(atIndex = 0) {
            idx = Math.max(0, Math.min(atIndex, images.length - 1));
            render();

            __scrollY = window.scrollY || 0;
            document.body.classList.add("modal-open");
            // iOS fix: صفحه رو همونجا فریز کن
            document.body.style.top = `-${__scrollY}px`;

            modal.classList.add("show");
            modal.setAttribute("aria-hidden", "false");
        }

        function close() {
            modal.classList.remove("show");
            modal.setAttribute("aria-hidden", "true");

            document.body.classList.remove("modal-open");
            const top = document.body.style.top;
            document.body.style.top = "";
            // برگرد به همون اسکرول قبلی
            window.scrollTo(0, __scrollY);

            document.body.style.overflow = "";
        }

        function setIndex(i) {
            idx = (i + images.length) % images.length;
            render();
        }

        function render() {
            const item = images[idx];
            if (!item) return;

            modalMainImg.src = item.full;
            modalMainImg.alt = item.alt || "";

            // thumbs
            modalThumbs.innerHTML = images.map((it, i) => `
      <button type="button" class="${i === idx ? "is-active" : ""}" data-i="${i}">
        <img src="${it.thumb}" alt="${it.alt || ""}" loading="lazy" decoding="async">
      </button>
    `).join("");

            // sync main page image too (optional but خیلی خوبه)
            // وقتی داخل مودال عوض شد، main هم همزمان عوض میشه
            const fakeBtn = {dataset: {full: item.full, zoom: item.zoom}};
            // دستی مثل activateThumb، ولی بدون تغییر کلاس‌ها
            if (window.__tlpSetMainFromModal) window.__tlpSetMainFromModal(item);
        }

        // close by click on backdrop or close button
        modal.addEventListener("click", (e) => {
            const t = e.target;
            if (t?.dataset?.close === "1") close();
        });

        // thumbs click inside modal
        modalThumbs.addEventListener("click", (e) => {
            const btn = e.target.closest("button[data-i]");
            if (!btn) return;
            setIndex(Number(btn.dataset.i || 0));
        });

        // nav buttons
        modal.querySelector(".tlp-modal-nav.prev")?.addEventListener("click", () => setIndex(idx - 1));
        modal.querySelector(".tlp-modal-nav.next")?.addEventListener("click", () => setIndex(idx + 1));

        // keyboard
        document.addEventListener("keydown", (e) => {
            if (!modal.classList.contains("show")) return;
            if (e.key === "Escape") close();
            if (e.key === "ArrowLeft") setIndex(idx + 1);  // RTL حس بهتر
            if (e.key === "ArrowRight") setIndex(idx - 1);
        });

        // expose open for thumb overlay
        window.__tlpOpenGalleryModal = open;
    })();

    // Form submit validation
    if (form) {
        form.addEventListener("submit", (e) => {
            if (qtyInput) {
                const min = Number(qtyInput.min || 1);
                const max = Number(qtyInput.max || 99);
                qtyInput.value = String(clamp(Number(qtyInput.value || 1), min, max));
            }

            const vid = hiddenVid?.value || "";
            const sizeNeeded = selectedColorId && isSizeRequired(selectedColorId);
            if (!vid || (sizeNeeded && !selectedSizeId)) {
                e.preventDefault();
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
    if (!btn) return;

    const productId = btn.dataset.productId;
    const url = btn.dataset.statusUrl;
    const icon = btn.querySelector("i");

    if (!productId || !url || !icon) return;

    fetch(`${url}?product_id=${productId}`, {headers: {"X-Requested-With": "XMLHttpRequest"}})
        .then((res) => res.json())
        .then((data) => {
            const textEl = btn.querySelector("span");

            if (data.in_wishlist) {
                icon.classList.remove("bi-heart");
                icon.classList.add("bi-heart-fill");
                btn.classList.add("added");
                if (textEl) textEl.textContent = "حذف از علاقه‌مندی‌ها";
            } else {
                icon.classList.remove("bi-heart-fill");
                icon.classList.add("bi-heart");
                btn.classList.remove("added");
                if (textEl) textEl.textContent = "افزودن به لیست علاقه‌مندی";
            }

            const badge = document.querySelector(".wishlist-count");
            if (badge) badge.textContent = data.count ?? 0;
        })
        .catch((err) => console.error("Wishlist status error:", err));
});


// ======================= FLASH MESSAGES AUTO HIDE =======================
document.addEventListener("DOMContentLoaded", function () {
    const messages = document.querySelectorAll(".flash-message");
    messages.forEach((msg) => {
        setTimeout(() => {
            msg.style.opacity = "0";
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
    if (typeof Chart === "undefined") return;

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

    const labels = labelsRaw.map((d) => {
        try {
            const dt = new Date(d);
            return dt.toLocaleDateString("fa-IR");
        } catch {
            return d;
        }
    });

    const rootStyles = getComputedStyle(document.documentElement);
    const colorMin = rootStyles.getPropertyValue("--chart-min").trim() || rootStyles.getPropertyValue("--line").trim() || "#2563eb";
    const colorAvg = rootStyles.getPropertyValue("--chart-avg").trim() || "#22c55e";
    const gridColor = rootStyles.getPropertyValue("--grid").trim() || "#eff3f8";
    const axisColor = rootStyles.getPropertyValue("--axis-muted").trim() || "#9ca3af";
    const fillBg = rootStyles.getPropertyValue("--chart-fill").trim() || "rgba(250,106,53,0.08)";

    const meta = chartData.meta || {};
    const minY = meta.min_y ?? meta.min_overall;
    const maxY = meta.max_y ?? meta.max_overall;

    const ctx = canvas.getContext("2d");
    if (canvas._priceChartInstance) canvas._priceChartInstance.destroy();

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
            backgroundColor: fillBg,
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
        data: {labels, datasets},
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    labels: {usePointStyle: true, boxWidth: 8, boxHeight: 8},
                },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            const val = ctx.parsed.y || 0;
                            const title = ctx.dataset.label || "";
                            return `${title}: ${val.toLocaleString("fa-IR")} تومان`;
                        },
                    },
                },
            },
            scales: {
                x: {
                    grid: {display: false},
                    ticks: {color: axisColor, maxRotation: 0, autoSkip: true, maxTicksLimit: 6},
                },
                y: {
                    grid: {color: gridColor},
                    ticks: {
                        color: axisColor,
                        callback: function (value) {
                            return value.toLocaleString("fa-IR");
                        },
                    },
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


// ----------------------------------------

// /* ======================= PRODUCT: Variant resolution + live pricing + form wiring ======================= */
// (function () {
//   'use strict';
//
//   // ---------- Shorthands ----------
//   const $  = (sel, root = document) => root.querySelector(sel);
//   const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
//
//   // ---------- Elements ----------
//   const form         = $("#add-to-cart-form");
//   const hiddenVid    = $("#variant_id");
//   const btnAdd       = $("#btn-add");
//   const qtyInput     = $("#qty");
//   const colorWrap    = $("#color-swatches");
//   const sizeSelect   = $("#size");
//   const mainImg      = $("#tlp-main");
//   const stickyImg    = $("#sticky-img");
//   // قیمت/تخفیف UI
//   const elPriceNum   = $("#price-num");
//   const elCompareNum = $("#compare-num");
//   const elSaveBox    = $("#price-save");
//   const elOffBadge   = $("#off-badge");
//   const elOffAmount  = $("#off-amount");
//   const lowStockEl   = $(".low-stock");
//
//   // ---------- Data from template (JSON tags) ----------
//   // variant-matrix: { matrix: { "<color_id>": { "<size_id|OS>": { price, stock, sku, compare_at?, variant_id? } } , sizes: {...}} }
//   // variant-prices: { "<variant_id>": { price, stock, sku, compare_at? } }
//   function readJSON(id) {
//     const el = document.getElementById(id);
//     if (!el) return null;
//     try { return JSON.parse(el.textContent || el.innerText || 'null'); } catch { return null; }
//   }
//   const matrixObj = readJSON('variant-matrix') || {};
//   const vprices   = readJSON('variant-prices') || {};
//   const M         = matrixObj.matrix || {};
//   const SIZES_META= matrixObj.sizes  || {};
//
//   // optional API endpoint (for precise pricing after optimistic update)
//   const priceApi  = $("#price-api")?.dataset?.url || null;
//
//   // ---------- Helpers ----------
//   const intcomma  = (n) => (Number.isFinite(n) ? n.toLocaleString("fa-IR") : "");
//   const clamp     = (x, a, b) => Math.min(Math.max(x, a), b);
//
//   function isSizeRequired(colorId) {
//     const row = M[String(colorId)] || {};
//     const keys = Object.keys(row || {});
//     if (!keys.length) return false;
//     // اگر کلید «OS» تنها گزینه نباشد، سایز اجباری است
//     return !(keys.length === 1 && keys[0] === "OS");
//   }
//
//   function resolveVariantCell(colorId, sizeId) {
//     if (!colorId) return null;
//     const row = M[String(colorId)] || {};
//     // اگر سایز انتخاب نشده، تلاش کن از OS یا اولین کلید پر شود
//     let key = sizeId || (row["OS"] ? "OS" : Object.keys(row)[0]);
//     if (!key) return null;
//     return row[String(key)] || null;
//   }
//
//   function resolveVariantId(colorId, sizeId) {
//     const cell = resolveVariantCell(colorId, sizeId);
//     if (!cell) return null;
//     // ترجیح با variant_id در ماتریس؛ در غیر این صورت اگر فقط یک کلید در vprices با sku match شد.
//     if (cell.variant_id) return String(cell.variant_id);
//
//     // fallback: اگر cell.sku داریم و در vprices دقیقاً یک واریانت با همان sku یافت شد
//     if (cell.sku) {
//       const matches = Object.entries(vprices).filter(([, v]) => (v && v.sku) === cell.sku);
//       if (matches.length === 1) return String(matches[0][0]);
//     }
//     return null;
//   }
//
//   function setPriceUI({ finalPrice, basePrice, discountPercent, discountAmount }) {
//     if (elPriceNum) elPriceNum.textContent = intcomma(finalPrice || 0);
//
//     const hasDiscount = !!(basePrice && finalPrice && finalPrice < basePrice);
//     if (!elSaveBox || !elCompareNum || !elOffBadge || !elOffAmount) return;
//
//     if (hasDiscount) {
//       elCompareNum.textContent = intcomma(basePrice);
//       elOffBadge.textContent   = `${Math.round(discountPercent || 0)}٪ تخفیف`;
//       elOffAmount.textContent  = discountAmount
//         ? `مبلغ کسرشده: ${intcomma(discountAmount)} تومان`
//         : "";
//       elSaveBox.style.display  = "";
//     } else {
//       elSaveBox.style.display  = "none";
//       elCompareNum.textContent = "";
//       elOffBadge.textContent   = "";
//       elOffAmount.textContent  = "";
//     }
//   }
//
//   function optimisticUpdate(variantId, cell) {
//     // اولویت با vprices؛ اگر نبود از cell استفاده کن
//     const cached = vprices[String(variantId)] || cell || {};
//     const finalPrice = Number(cached.price ?? 0);
//     const basePrice  = Number(cached.compare_at ?? 0);
//     const hasDisc    = basePrice && finalPrice && finalPrice < basePrice;
//     const discountAmount  = hasDisc ? (basePrice - finalPrice) : 0;
//     const discountPercent = hasDisc ? ((discountAmount / basePrice) * 100) : 0;
//
//     setPriceUI({
//       finalPrice,
//       basePrice: hasDisc ? basePrice : null,
//       discountPercent: hasDisc ? discountPercent : null,
//       discountAmount: hasDisc ? discountAmount : null
//     });
//   }
//
//   async function fetchAndFix(variantId) {
//     if (!priceApi || !variantId) return;
//     try {
//       const url = new URL(priceApi, window.location.origin);
//       url.searchParams.set("variant", String(variantId));
//       const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
//       if (!res.ok) return;
//       const data = await res.json();
//       if (!data || data.ok === false) return;
//
//       setPriceUI({
//         finalPrice: Number(data.price_final ?? 0),
//         basePrice:  (data.price_base ?? null),
//         discountPercent: (data.discount_percent ?? null),
//         discountAmount:  (data.discount_amount  ?? null)
//       });
//     } catch (_e) {
//       // سکوت: optimistic کفایت می‌کند
//     }
//   }
//
//   function updateLowStock(stock) {
//     if (!lowStockEl) return;
//     if (stock > 0 && stock <= 5) {
//       lowStockEl.style.display = '';
//       lowStockEl.textContent = 'تنها ' + intcomma(stock) + ' عدد در انبار باقی مانده';
//     } else {
//       lowStockEl.style.display = 'none';
//     }
//   }
//
//   function enableAdd(enabled) {
//     if (!btnAdd) return;
//     btnAdd.disabled = !enabled;
//     btnAdd.classList.toggle('is-disabled', !enabled);
//     btnAdd.setAttribute('aria-disabled', (!enabled).toString());
//   }
//  function activateThumb(btn) {
//     if (!btn || !mainImg) return;
//
//     // آدرس تصویر بزرگ
//     const full = btn.dataset.full || btn.querySelector("img")?.getAttribute("src");
//     if (full) {
//       mainImg.setAttribute("src", full);
//       if (stickyImg) {
//         stickyImg.setAttribute("src", full);
//       }
//     }
//
//     // کلاس active + aria-pressed روی تامب‌ها
//     $$(".thumb").forEach(t => {
//       const isActive = t === btn;
//       t.classList.toggle("is-active", isActive);
//       t.setAttribute("aria-pressed", isActive ? "true" : "false");
//     });
//   }
//
//  function swapImageForColor(colorId) {
//     if (!colorId) return;
//     // سعی می‌کنیم تامبی پیدا کنیم که رنگش با colorId یکی است
//     let btn = document.querySelector(`.thumb[data-color-id="${colorId}"]`);
//     // اگر نبود، حداقل اولین تامب را فعال کن
//     if (!btn) {
//       btn = document.querySelector(".thumb");
//     }
//     if (btn) {
//       activateThumb(btn);
//     }
//   }
//
// //   zoom box
// (function () {
//   const stage = document.getElementById("tlp-stage") || document.querySelector(".tlp-gallery .stage");
//   const mainImg = document.getElementById("tlp-main");
//   const lens = stage ? stage.querySelector(".zoom-lens") : null;
//
//   const zoomBox = document.getElementById("tlp-zoom-box");
//   const zoomImg = document.getElementById("tlp-zoom-img");
//
//   if (!stage || !mainImg || !lens || !zoomBox || !zoomImg) return;
//
//   // روی موبایل/تاچ: زوم هاور رو غیرفعال کن
//   const canHover = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
//   if (!canHover) return;
//
//   let imgNaturalW = 0, imgNaturalH = 0;
//
//   function preloadNatural(src) {
//     return new Promise((resolve) => {
//       const im = new Image();
//       im.onload = () => resolve({ w: im.naturalWidth || 0, h: im.naturalHeight || 0 });
//       im.onerror = () => resolve({ w: 0, h: 0 });
//       im.src = src;
//     });
//   }
//
//   async function refreshZoomSource() {
//     const src = mainImg.currentSrc || mainImg.src;
//     const nat = await preloadNatural(src);
//     imgNaturalW = nat.w;
//     imgNaturalH = nat.h;
//     zoomImg.style.backgroundImage = `url("${src}")`;
//   }
//
//   function placeZoomBox() {
//     const r = stage.getBoundingClientRect();
//     const gap = 14;
//     const boxW = zoomBox.offsetWidth || 420;
//     const boxH = zoomBox.offsetHeight || 420;
//
//     // در RTL بهتره پنجره زوم سمت چپ stage بیفته (مثل نمونه‌هایی که thumbs راست هستند)
//     let left = r.left - gap - boxW;
//     if (left < 8) left = r.right + gap; // اگر جا نبود، بنداز سمت راست
//
//     let top = r.top;
//     // جمع‌وجور کردن داخل viewport
//     const maxTop = window.innerHeight - boxH - 8;
//     if (top > maxTop) top = Math.max(8, maxTop);
//
//     zoomBox.style.left = `${left}px`;
//     zoomBox.style.top = `${top}px`;
//   }
//
//   function clamp(v, min, max) {
//     return Math.max(min, Math.min(max, v));
//   }
//
//   function update(e) {
//     // مختصات روی خود تصویر (نه کل stage) تا اگر object-fit:contain بود دقیق‌تر شود
//     const imgRect = mainImg.getBoundingClientRect();
//     const x = e.clientX - imgRect.left;
//     const y = e.clientY - imgRect.top;
//
//     if (x < 0 || y < 0 || x > imgRect.width || y > imgRect.height) return;
//
//     // اندازه لنز: حدوداً 35% از تصویر (قابل تنظیم)
//     const lensW = Math.max(90, imgRect.width * 0.35);
//     const lensH = Math.max(90, imgRect.height * 0.35);
//     lens.style.width = `${lensW}px`;
//     lens.style.height = `${lensH}px`;
//
//     // مرکز لنز روی ماوس
//     const lensLeft = clamp(x - lensW / 2, 0, imgRect.width - lensW);
//     const lensTop = clamp(y - lensH / 2, 0, imgRect.height - lensH);
//
//     // انتقال لنز (نسبت به stage)
//     const stageRect = stage.getBoundingClientRect();
//     const leftOnStage = (imgRect.left - stageRect.left) + lensLeft;
//     const topOnStage = (imgRect.top - stageRect.top) + lensTop;
//
//     lens.style.transform = `translate(${leftOnStage}px, ${topOnStage}px)`;
//
//     // درصد موقعیت برای بکگراند پنجره زوم
//     const px = (lensLeft + lensW / 2) / imgRect.width;
//     const py = (lensTop + lensH / 2) / imgRect.height;
//
//     // میزان زوم: هرچی بزرگتر، زوم بیشتر (۲.۲ خوبه)
//     const zoomFactor = 2.2;
//
//     // بکگراند سایز بر اساس اندازه‌ی نمایش داده شده تصویر
//     const bgW = imgRect.width * zoomFactor;
//     const bgH = imgRect.height * zoomFactor;
//     zoomImg.style.backgroundSize = `${bgW}px ${bgH}px`;
//
//     // بکگراند پوزیشن
//     zoomImg.style.backgroundPosition = `${px * 100}% ${py * 100}%`;
//   }
//
//   async function onEnter() {
//     await refreshZoomSource();
//     stage.classList.add("zooming");
//     zoomBox.classList.add("show");
//     placeZoomBox();
//   }
//
//   function onLeave() {
//     stage.classList.remove("zooming");
//     zoomBox.classList.remove("show");
//   }
//
//   // رویدادها
//   stage.addEventListener("mouseenter", onEnter);
//   stage.addEventListener("mousemove", update);
//   stage.addEventListener("mouseleave", onLeave);
//   window.addEventListener("scroll", () => zoomBox.classList.contains("show") && placeZoomBox(), { passive: true });
//   window.addEventListener("resize", () => zoomBox.classList.contains("show") && placeZoomBox());
//
//   // وقتی تصویر عوض شد (کلیک روی تامب‌ها)، سورس زوم هم آپدیت شود
//   mainImg.addEventListener("load", () => {
//     if (zoomBox.classList.contains("show")) refreshZoomSource();
//   });
// })();
//
//
//   // ---------- State ----------
//   let selectedColorId = (colorWrap?.querySelector(".active")?.dataset?.colorId) || null;
//   let selectedSizeId  = (sizeSelect && sizeSelect.value && sizeSelect.value !== "#") ? sizeSelect.value : null;
//
//   // ---------- Main selection handler ----------
//   async function onSelectionChange() {
//     // اگر رنگی انتخاب نشده، اولین رنگ موجود را انتخابِ منطقی کن
//     if (!selectedColorId) {
//       const first = colorWrap?.querySelector('a[data-color-id]')?.getAttribute('data-color-id');
//       if (first) selectedColorId = first;
//     }
//
//     // اگر سایز لازم است ولی انتخاب نشده، فعلاً دکمه را غیرفعال کن
//     if (selectedColorId && isSizeRequired(selectedColorId) && !selectedSizeId) {
//       enableAdd(false);
//       if (hiddenVid) hiddenVid.value = "";
//       return;
//     }
//
//     // رزولوشن واریانت
//     const cell = resolveVariantCell(selectedColorId, selectedSizeId);
//     const variantId = resolveVariantId(selectedColorId, selectedSizeId);
//
//     // ست کردن hidden
//     if (hiddenVid) hiddenVid.value = variantId ? String(variantId) : "";
//
//     // تصویر متناسب رنگ
//     if (selectedColorId) swapImageForColor(selectedColorId);
//
//     // کنترل موجودی و فعال/غیرفعال کردن دکمه
//     const stock = Number(cell?.stock ?? vprices[variantId]?.stock ?? 0);
//     updateLowStock(stock);
//     enableAdd(!!(variantId && stock > 0));
//
//     // قیمت: optimistic و سپس دقیق از API
//     if (variantId) {
//       optimisticUpdate(variantId, cell);
//       fetchAndFix(variantId);
//     }
//   }
//
//   // ---------- Events ----------
//   // رنگ
//  if (colorWrap) {
//     $$("#color-swatches a[data-color-id]").forEach(a => {
//       // انتقال color-id به dataset برای اطمینان
//       if (!a.dataset.colorId) a.dataset.colorId = a.getAttribute("data-color-id") || "";
//       a.addEventListener("click", (ev) => {
//         ev.preventDefault();
//         $$("#color-swatches a").forEach(x => x.classList.remove("active"));
//         a.classList.add("active");
//         selectedColorId = a.dataset.colorId || null;
//         // اگر سایز OS تنها گزینه است، سایز را null نگه می‌داریم
//         if (!isSizeRequired(selectedColorId)) selectedSizeId = null;
//         onSelectionChange();
//       });
//     });
//   }
//
//   // سایز
//   if (sizeSelect) {
//     sizeSelect.addEventListener("change", () => {
//       const v = sizeSelect.value;
//       selectedSizeId = (v && v !== "#") ? v : null;
//       onSelectionChange();
//     });
//   }
//
//   // گالری تصاویر: کلیک روی تامب‌ها
//   $$(".thumbs .thumb").forEach(btn => {
//     btn.addEventListener("click", (e) => {
//       e.preventDefault();
//       activateThumb(btn);
//     });
//   });
//
//   // اعتبارسنجی نهایی فرم قبل از ارسال
//   if (form) {
//     form.addEventListener("submit", (e) => {
//       // تعداد
//       if (qtyInput) {
//         const min = Number(qtyInput.min || 1);
//         const max = Number(qtyInput.max || 99);
//         qtyInput.value = String(clamp(Number(qtyInput.value || 1), min, max));
//       }
//
//       // واریانت
//       const vid = hiddenVid?.value || "";
//       const sizeNeeded = selectedColorId && isSizeRequired(selectedColorId);
//       if (!vid || (sizeNeeded && !selectedSizeId)) {
//         e.preventDefault();
//         // پیام ساده؛ اگر سیستم نوتیفیکیشن داری، اینجا جایگزین کن
//         alert(sizeNeeded && !selectedSizeId ? "لطفاً سایز را انتخاب کنید." : "لطفاً یک واریانت معتبر انتخاب کنید.");
//         enableAdd(false);
//         return false;
//       }
//     });
//   }
//
//   // ---------- Initial run ----------
//   onSelectionChange();
//
// })();
//
//
// // ======================= WISHLIST STATUS (icon + navbar count) =======================
// document.addEventListener("DOMContentLoaded", function () {
//     const btn = document.querySelector(".btn-wishlist");
//     if (!btn) return; // اگر روی صفحه دکمه وجود نداشت
//
//     const productId = btn.dataset.productId;
//     const url = btn.dataset.statusUrl;  // باید در HTML بگذاری
//     const icon = btn.querySelector("i");
//
//     if (!productId || !url || !icon) return;
//
//     fetch(`${url}?product_id=${productId}`, {
//         headers: { "X-Requested-With": "XMLHttpRequest" }
//     })
//     .then(res => res.json())
//     .then(data => {
//         // ست کردن آیکون
//         if (data.in_wishlist) {
//             icon.classList.remove("bi-heart");
//             icon.classList.add("bi-heart-fill");
//             btn.classList.add("added");
//             btn.querySelector("span").textContent = "حذف از علاقه‌مندی‌ها";
//         } else {
//             icon.classList.remove("bi-heart-fill");
//             icon.classList.add("bi-heart");
//             btn.classList.remove("added");
//             btn.querySelector("span").textContent = "افزودن به لیست علاقه‌مندی";
//         }
//
//         // آپدیت badge نوبار
//         const badge = document.querySelector(".wishlist-count");
//         if (badge) {
//             badge.textContent = data.count ?? 0;
//         }
//     })
//     .catch(err => console.error("Wishlist status error:", err));
// });
//
//
// // ------------- Compare Flag ----------------
//
// document.addEventListener("DOMContentLoaded", function() {
//     const messages = document.querySelectorAll(".flash-message");
//     messages.forEach(msg => {
//         // بعد 5 ثانیه شروع به کم رنگ شدن می‌کنیم
//         setTimeout(() => {
//             msg.style.opacity = '0';
//             // بعد از اتمام انیمیشن حذف از DOM
//             setTimeout(() => msg.remove(), 800);
//         }, 5000);
//     });
// });
//
// // ================== Price History Chart ==================
// function initPriceChart() {
//   const jsonScript = document.getElementById("price-chart-data");
//   const canvas = document.getElementById("priceLineChart");
//   const card = document.querySelector("#line-chart");
//
//   if (!jsonScript || !canvas) return;
//
//   let chartData;
//   try {
//     chartData = JSON.parse(jsonScript.textContent || "{}");
//   } catch (e) {
//     console.error("price-chart-data JSON parse error", e);
//     return;
//   }
//
//   const labelsRaw = chartData.labels || [];
//   const minPrices = chartData.min_prices || [];
//   const avgPrices = chartData.avg_prices || [];
//
//   if (!labelsRaw.length || (!minPrices.length && !avgPrices.length)) {
//     if (card) {
//       card.innerHTML =
//         '<div class="p-3 text-muted" style="font-size:0.9rem;">برای این محصول هنوز سابقهٔ قیمت ثبت نشده است.</div>';
//     }
//     return;
//   }
//
//   // تبدیل تاریخ‌ها به فرمت فارسی قابل‌خواندن
//   const labels = labelsRaw.map((d) => {
//     try {
//       const dt = new Date(d);
//       return dt.toLocaleDateString("fa-IR");
//     } catch (e) {
//       return d;
//     }
//   });
//
//   const rootStyles = getComputedStyle(document.documentElement);
//   const colorMin =
//     rootStyles.getPropertyValue("--chart-min").trim() ||
//     rootStyles.getPropertyValue("--line").trim() ||
//     "#2563eb"; // آبی
//   const colorAvg =
//     rootStyles.getPropertyValue("--chart-avg").trim() ||
//     "#22c55e"; // سبز
//   const gridColor =
//     rootStyles.getPropertyValue("--grid").trim() || "#eff3f8";
//   const axisColor =
//     rootStyles.getPropertyValue("--axis-muted").trim() || "#9ca3af";
//   const fillBg =
//     rootStyles.getPropertyValue("--chart-fill").trim() || "rgba(250,106,53,0.08)";
//
//   const meta = chartData.meta || {};
//   const minY = meta.min_y ?? meta.min_overall;
//   const maxY = meta.max_y ?? meta.max_overall;
//
//   const ctx = canvas.getContext("2d");
//
//   if (canvas._priceChartInstance) {
//     canvas._priceChartInstance.destroy();
//   }
//
//   const datasets = [];
//
//   if (minPrices.length) {
//     datasets.push({
//       label: "کمترین قیمت",
//       data: minPrices,
//       borderColor: colorMin,
//       backgroundColor: colorMin,
//       pointBackgroundColor: colorMin,
//       pointRadius: 3,
//       pointHoverRadius: 4,
//       borderWidth: 2,
//       tension: 0.3,
//     });
//   }
//
//   if (avgPrices.length) {
//     datasets.push({
//       label: "میانگین قیمت",
//       data: avgPrices,
//       borderColor: colorAvg,
//       backgroundColor: fillBg, // برای fill زیر منحنی
//       pointBackgroundColor: colorAvg,
//       pointRadius: 3,
//       pointHoverRadius: 4,
//       borderWidth: 2,
//       tension: 0.3,
//       fill: "origin",
//     });
//   }
//
//   const chart = new Chart(ctx, {
//     type: "line",
//     data: {
//       labels: labels,
//       datasets: datasets,
//     },
//     options: {
//       responsive: true,
//       maintainAspectRatio: false,
//       plugins: {
//         legend: {
//           display: true,
//           labels: {
//             usePointStyle: true,
//             boxWidth: 8,
//             boxHeight: 8,
//           },
//         },
//         tooltip: {
//           callbacks: {
//             label: function (ctx) {
//               const val = ctx.parsed.y || 0;
//               const title = ctx.dataset.label || "";
//               return (
//                 title +
//                 ": " +
//                 val.toLocaleString("fa-IR") +
//                 " تومان"
//               );
//             },
//           },
//         },
//       },
//       scales: {
//         x: {
//           grid: { display: false },
//           ticks: {
//             color: axisColor,
//             maxRotation: 0,
//             autoSkip: true,
//             maxTicksLimit: 6,
//           },
//         },
//         y: {
//           grid: { color: gridColor },
//           ticks: {
//             color: axisColor,
//             callback: function (value) {
//               return value.toLocaleString("fa-IR");
//             },
//           },
//           // محور Y بین کمترین و بیشترین قیمت (با کمی حاشیه)
//           min: typeof minY === "number" ? minY : undefined,
//           max: typeof maxY === "number" ? maxY : undefined,
//         },
//       },
//     },
//   });
//
//   canvas._priceChartInstance = chart;
// }
//
// document.addEventListener("DOMContentLoaded", function () {
//   initPriceChart();
// });
//
