// کنترل تب‌ها فقط برای لینک‌های داخلی (دارای #)
document.addEventListener("DOMContentLoaded", function () {
    const links = document.querySelectorAll('.dashboard-menu li a.tab-trigger-link');
    const tabs = document.querySelectorAll('.tab-content .tab-pane');

    links.forEach(link => {
        link.addEventListener('click', function (e) {
            const target = this.getAttribute('href');

            // فقط اگر لینک به تب داخلی (#) اشاره دارد، از رفتار پیش‌فرض جلوگیری کن
            if (target && target.startsWith('#')) {
                e.preventDefault();

                // حذف active از همه لینک‌ها
                document.querySelectorAll('.dashboard-menu li a').forEach(l => l.classList.remove('active'));
                this.classList.add('active');

                // نمایش تب مربوطه و مخفی کردن سایر تب‌ها
                tabs.forEach(tab => tab.classList.remove('show', 'active'));
                const pane = document.querySelector(target);
                if (pane) {
                    pane.classList.add('show', 'active');
                }
            }
        });
    });
});


// ✅ اعتبارسنجی فرم سمت کلاینت
(function () {
    'use strict';
    window.addEventListener('load', function () {
        const forms = document.getElementsByClassName('needs-validation');
        Array.prototype.filter.call(forms, function (form) {
            form.addEventListener('submit', function (event) {
                if (form.checkValidity() === false) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add('was-validated');
            }, false);
        });

        // محدود کردن ورودی شماره تلفن به اعداد و شروع با 09
        const phoneInput = document.querySelector('input[name="phone"]');
        if (phoneInput) {
            phoneInput.addEventListener('input', function () {
                this.value = this.value.replace(/[^0-9]/g, '');
                if (this.value.length > 11) this.value = this.value.slice(0, 11);
                if (this.value.length > 0 && this.value[0] !== '0') {
                    this.value = '09' + this.value.slice(1);
                } else if (this.value.length > 1 && this.value.slice(0, 2) !== '09') {
                    this.value = '09' + this.value.slice(2);
                }
            });

            phoneInput.addEventListener('keypress', function (e) {
                if (e.charCode !== 0 && (e.charCode < 48 || e.charCode > 57)) {
                    e.preventDefault();
                }
            });
        }

        // محدود کردن ورودی کد ملی به اعداد و دقیقاً ۱۰ رقم
        const nationalIdInput = document.querySelector('input[name="national_id"]');
        if (nationalIdInput) {
            nationalIdInput.addEventListener('input', function () {
                this.value = this.value.replace(/[^0-9]/g, '');
                if (this.value.length > 10) this.value = this.value.slice(0, 10);
            });

            nationalIdInput.addEventListener('keypress', function (e) {
                if (e.charCode !== 0 && (e.charCode < 48 || e.charCode > 57)) {
                    e.preventDefault();
                }
            });
        }
    }, false);
})();


// 🔸 اسکرول خودکار به کارت هدف در موبایل
document.addEventListener('DOMContentLoaded', function () {
    if (window.innerWidth <= 992) { // فقط در موبایل و تبلت
        const hash = window.location.hash; // مثلا #personal-info-card
        if (hash) {
            const target = document.querySelector(hash);
            if (target) {
                setTimeout(() => {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 500); // کمی تأخیر تا DOM کامل لود شود
            }
        }
    }
});


