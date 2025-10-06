document.addEventListener("DOMContentLoaded", function () {
    const links = document.querySelectorAll('.dashboard-menu li a.tab-trigger-link');
    const tabs = document.querySelectorAll('.tab-content .tab-pane');

    links.forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            // حذف کلاس active از همه لینک‌ها
            document.querySelectorAll('.dashboard-menu li a').forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            // نمایش تب مربوطه و مخفی کردن سایر تب‌ها
            tabs.forEach(tab => tab.classList.remove('show', 'active'));
            const target = this.getAttribute('href');
            const pane = document.querySelector(target);
            if (pane) {
                pane.classList.add('show', 'active');
            }
        });
    });
});

// اعتبارسنجی فرم در سمت کلاینت
(function () {
    'use strict';
    window.addEventListener('load', function () {
        var forms = document.getElementsByClassName('needs-validation');
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
            phoneInput.addEventListener('input', function (e) {
                // فقط اعداد را نگه می‌دارد
                this.value = this.value.replace(/[^0-9]/g, '');
                // محدود کردن به ۱۱ رقم
                if (this.value.length > 11) {
                    this.value = this.value.slice(0, 11);
                }
                // اطمینان از شروع با 09
                if (this.value.length > 0 && this.value[0] !== '0') {
                    this.value = '09' + this.value.slice(1);
                } else if (this.value.length > 1 && this.value.slice(0, 2) !== '09') {
                    this.value = '09' + this.value.slice(2);
                }
            });

            phoneInput.addEventListener('keypress', function (e) {
                // فقط اجازه ورود اعداد
                if (e.charCode !== 0 && (e.charCode < 48 || e.charCode > 57)) {
                    e.preventDefault();
                }
            });
        }

        // محدود کردن ورودی کد ملی به اعداد و دقیقاً ۱۰ رقم
        const nationalIdInput = document.querySelector('input[name="national_id"]');
        if (nationalIdInput) {
            nationalIdInput.addEventListener('input', function (e) {
                // فقط اعداد را نگه می‌دارد
                this.value = this.value.replace(/[^0-9]/g, '');
                // محدود کردن به ۱۰ رقم
                if (this.value.length > 10) {
                    this.value = this.value.slice(0, 10);
                }
            });

            nationalIdInput.addEventListener('keypress', function (e) {
                // فقط اجازه ورود اعداد
                if (e.charCode !== 0 && (e.charCode < 48 || e.charCode > 57)) {
                    e.preventDefault();
                }
            });
        }
    }, false);
})();