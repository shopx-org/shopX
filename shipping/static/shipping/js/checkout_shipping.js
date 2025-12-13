// /* checkout_shipping.js */
//
// // به‌روزرسانی سربرگ سبد خرید (تعداد آیتم‌ها و مبلغ کل)
// (function () {
//     var $badge = $('.cart-dropdown .cart-count');
//     var $total = $('.cart-dropdown .cart-total-price');
//
//     if (!$badge.length && !$total.length) {
//         return;
//     }
//
//     $.ajax({
//         url: '/cart/api/header-summary/',
//         method: 'GET',
//         headers: { 'X-Requested-With': 'XMLHttpRequest' }
//     }).done(function (data) {
//         if (!data || !data.ok || !data.summary) return;
//
//         var sum = data.summary;
//
//         if ($badge.length) {
//             $badge.text(sum.items_count || 0);
//         }
//
//         if ($total.length) {
//             var formatter = new Intl.NumberFormat('fa-IR');
//             var t = sum.total || 0;
//             $total.text(formatter.format(t) + ' تومان');
//         }
//     }).fail(function () {
//         // در صورت خطا چیزی تغییر نده
//     });
// })();
//
// // گرفتن CSRF از کوکی
// function getCookie(name) {
//     let cookieValue = null;
//     if (document.cookie && document.cookie !== "") {
//         const cookies = document.cookie.split(";");
//         for (let i = 0; i < cookies.length; i++) {
//             const cookie = cookies[i].trim();
//             if (cookie.substring(0, name.length + 1) === (name + "=")) {
//                 cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
//                 break;
//             }
//         }
//     }
//     return cookieValue;
// }
//
// document.addEventListener("DOMContentLoaded", function () {
//     // انتخاب همه‌ی رادیوهای روش ارسال
//     const methodInputs = document.querySelectorAll('input[name="shipping_method"]');
//     // عناصر خلاصه‌ی سبد
//     const summaryBox = document.getElementById("summary");
//     const shipLine = document.getElementById("s-shipline");
//     const shipValue = document.getElementById("s-ship");
//     const totalValue = document.getElementById("s-total");
//
//     if (!methodInputs.length || !summaryBox || !shipLine || !shipValue || !totalValue) {
//         return;
//     }
//
//     const csrftoken = getCookie("csrftoken");
//
//     // قالب‌بندی رقم به تومان
//     function formatToman(num) {
//         const n = parseInt(num || 0, 10);
//         return n.toLocaleString("fa-IR") + " تومان";
//     }
//
//     // محاسبه و به‌روزرسانی مجموع جدید
//     function recalcTotal(shippingAmount) {
//         const sub = parseInt(summaryBox.dataset.sub || "0", 10);
//         const disc = parseInt(summaryBox.dataset.disc || "0", 10);
//         const svc = parseInt(summaryBox.dataset.svc || "0", 10);
//         const ship = parseInt(shippingAmount || "0", 10);
//
//         const total = (sub - disc) + svc + ship;
//         summaryBox.dataset.total = total;
//
//         shipLine.style.display = ship > 0 ? "flex" : "none";
//         shipValue.textContent = formatToman(ship);
//         totalValue.textContent = formatToman(total);
//     }
//
//     // ارسال درخواست AJAX برای گرفتن هزینه‌ی ارسال
//     function sendQuote(methodId) {
//         if (!window.shippingQuoteURL) {
//             return;
//         }
//
//         fetch(window.shippingQuoteURL, {
//             method: "POST",
//             headers: {
//                 "Content-Type": "application/json",
//                 "X-CSRFToken": csrftoken,
//                 "X-Requested-With": "XMLHttpRequest"
//             },
//             body: JSON.stringify({
//                 shipping_method_id: methodId
//             })
//         })
//         .then(res => res.json())
//         .then(data => {
//             if (!data.ok) {
//                 console.warn("Shipping quote error:", data.error);
//                 recalcTotal(0);
//                 return;
//             }
//             recalcTotal(data.shipping_amount);
//         })
//         .catch(err => {
//             console.error("Shipping quote exception:", err);
//             recalcTotal(0);
//         });
//     }
//
//     // رویداد تغییر برای هر رادیو
//     methodInputs.forEach(input => {
//         input.addEventListener("change", function () {
//             const methodId = this.value;
//             if (methodId) {
//                 sendQuote(methodId);
//             }
//         });
//
//         // اگر یک رادیو از قبل انتخاب شده باشد، همان ابتدا قیمت را می‌گیرد
//         if (input.checked) {
//             sendQuote(input.value);
//         }
//     });
// });