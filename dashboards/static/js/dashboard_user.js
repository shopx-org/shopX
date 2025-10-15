document.addEventListener("DOMContentLoaded", function () {
    // المنت‌ها
    const sendBtn = document.getElementById("send_otp_old");
    const verifyBtn = document.getElementById("verify_otp");
    const newPhoneInput = document.getElementById("new_phone");
    const codeInput = document.getElementById("otp_code");
    const otpStageArea = document.getElementById("otp_stage_area");
    const personalCard = document.getElementById("personal-info-card"); // برای درج پیام

    // حالت‌ها
    let stage = "send_old";
    let token = null;
    let isProcessing = false;

    // helper: نمایش پیام در بالای کارت (مثل messages جنگو)
    function showMessageInView(message, type = "info") {
        // type: 'info' | 'success' | 'error'
        if (!personalCard) {
            alert(message);
            return;
        }
        // حذف پیام قبلی
        const existing = personalCard.querySelector(".ajax-message-area");
        if (existing) existing.remove();

        const wrapper = document.createElement("div");
        wrapper.className = "ajax-message-area mb-3";

        let cls = "alert alert-info";
        if (type === "success") cls = "alert alert-success";
        else if (type === "error") cls = "alert alert-danger";

        wrapper.innerHTML = `<div class="${cls}" role="alert">${message}</div>`;
        // درج در بالای کارت (قبل از اولین child)
        personalCard.insertBefore(wrapper, personalCard.firstChild);
    }

    // جلوگیری از double-bind اگر JS چند بار اجرا شود:
    if (sendBtn && sendBtn.dataset.bound !== "1") {
        sendBtn.dataset.bound = "1";
        sendBtn.addEventListener("click", async function (e) {
            e.preventDefault();
            if (isProcessing) return;
            isProcessing = true;

            const newPhone = newPhoneInput.value.trim();
            if (!/^09\d{9}$/.test(newPhone)) {
                showMessageInView("شماره جدید معتبر نیست.", "error");
                isProcessing = false;
                return;
            }

            // disable button to prevent double click
            sendBtn.disabled = true;
            sendBtn.classList.add("disabled");

            try {
                const res = await fetch("/dashboard/change-phone-otp/", {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value,
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                    body: new URLSearchParams({stage, new_phone: newPhone})
                });
                const data = await res.json();

                if (data.status === "error") {
                    showMessageInView(data.message || "خطا در ارسال.", "error");
                } else if (data.status === "ok" && data.stage === "verify_old") {
                    token = data.token;
                    stage = "verify_old";
                    otpStageArea.style.display = "block";
                    codeInput.value = "";
                    showMessageInView(data.message || "کد ارسال شد.", "info");
                } else {
                    showMessageInView(data.message || "پاسخ نامعلوم از سرور.", "error");
                }

            } catch (err) {
                console.error("Send OTP error:", err);
                showMessageInView("خطا در ارتباط با سرور.", "error");
            }

            // re-enable after short delay
            setTimeout(() => {
                isProcessing = false;
                sendBtn.disabled = false;
                sendBtn.classList.remove("disabled");
            }, 1500);
        });
    }

    // bind verifyBtn
    if (verifyBtn && verifyBtn.dataset.bound !== "1") {
        verifyBtn.dataset.bound = "1";
        verifyBtn.addEventListener("click", async function (e) {
            e.preventDefault();
            if (isProcessing) return;
            isProcessing = true;

            const code = codeInput.value.trim();
            if (!/^\d{4}$/.test(code)) {
                showMessageInView("کد باید ۴ رقمی باشد.", "error");
                isProcessing = false;
                return;
            }

            // disable verify button briefly
            verifyBtn.disabled = true;
            verifyBtn.classList.add("disabled");

            try {
                const res = await fetch("/dashboard/change-phone-otp/", {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value,
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                    body: new URLSearchParams({
                        stage,
                        token,
                        code,
                        new_phone: newPhoneInput.value.trim()
                    })
                });
                const data = await res.json();

                if (data.status === "error") {
                    showMessageInView(data.message || "کد اشتباه یا خطا.", "error");
                } else if (data.status === "ok" && data.stage === "verify_new") {
                    token = data.token;
                    stage = "verify_new";
                    codeInput.value = "";
                    showMessageInView(data.message || "کد دوم ارسال شد.", "info");
                } else if (data.status === "done") {
                    showMessageInView(data.message || "شماره تغییر کرد.", "success");
                    // بعد از موفقیت صفحه را رفرش کن تا مقدار phone در template بروزرسانی شود
                    setTimeout(() => window.location.reload(), 900);
                } else {
                    showMessageInView(data.message || "پاسخ نامعلوم از سرور.", "error");
                }
            } catch (err) {
                console.error("Verify OTP error:", err);
                showMessageInView("خطا در ارتباط با سرور.", "error");
            }

            setTimeout(() => {
                isProcessing = false;
                verifyBtn.disabled = false;
                verifyBtn.classList.remove("disabled");
            }, 1200);
        });
    }
});

// -----------------------------
// 🧭 اسکرول نرم و هوشمند بدون # در URL (فعال برای موبایل و دسکتاپ)
// -----------------------------
document.addEventListener('DOMContentLoaded', function () {
    const sidebarLinks = document.querySelectorAll('a[data-scroll]');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function (e) {
            const targetSelector = this.getAttribute('data-scroll');
            const target = document.querySelector(targetSelector);
            const href = this.getAttribute('href');

            if (target) {
                e.preventDefault();
                target.scrollIntoView({behavior: 'smooth', block: 'start'});

                // حذف # از URL
                if (window.history.replaceState) {
                    window.history.replaceState(null, '', href);
                }
            } else {
                // اگر سکشن هنوز لود نشده بود (در تب یا lazy load)
                sessionStorage.setItem('scrollTarget', targetSelector);
            }
        });
    });

    // اگر کاربر از صفحه دیگری آمده و scrollTarget در sessionStorage بود
    const scrollTarget = sessionStorage.getItem('scrollTarget');
    if (scrollTarget) {
        const target = document.querySelector(scrollTarget);
        if (target) {
            setTimeout(() => {
                target.scrollIntoView({behavior: 'smooth', block: 'start'});
                sessionStorage.removeItem('scrollTarget');
            }, 500);
        }
    }
});
