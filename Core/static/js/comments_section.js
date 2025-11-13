document.addEventListener("DOMContentLoaded", function () {

    const form = document.getElementById("comment-form");
    const textArea = form.querySelector("textarea[name='text']");
    const parentInput = form.querySelector("input[name='parent_id']");

    // ✅ کلیک روی دکمه ریپلای
    document.querySelectorAll(".reply-btn").forEach(btn => {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            parentInput.value = this.dataset.parent;

            form.scrollIntoView({ behavior: "smooth" });
            textArea.focus();
        });
    });

    // ✅ ارسال AJAX
    form.addEventListener("submit", function (e) {
        e.preventDefault();

        const textValue = textArea.value.trim();

        // پاک کردن خطا قبلی
        const oldError = document.getElementById("comment-error");
        if (oldError) oldError.remove();

        // ✅ ولیدیشن سمت کاربر
        if (textValue.length < 3) {
            const err = document.createElement("div");
            err.id = "comment-error";
            err.className = "text-danger mt-2 fw-bold";
            err.innerText = "نظر باید حداقل ۳ کاراکتر باشد.";
            form.appendChild(err);
            return;
        }

        // ✅ ارسال AJAX با Fetch
        fetch(form.action, {
            method: "POST",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
            body: new FormData(form),
        })
        .then(res => res.json())
        .then(data => {
            // ✅ موفقیت
            if (data.status === "ok") {

                // پیام موفقیت
                const msg = document.createElement("div");
                msg.className = "text-success mt-2 fw-bold";
                msg.innerText = data.message;
                form.appendChild(msg);

                // پاک کردن فرم
                textArea.value = "";
                parentInput.value = "";

                // ✅ اضافه‌کردن کامنت جدید بدون رفرش
                if (data.new_html) {
                    const commentsWrapper = document.getElementById("comments-wrapper");
                    commentsWrapper.insertAdjacentHTML("beforeend", data.new_html);
                }

            } else {
                // ✅ خطا
                const err = document.createElement("div");
                err.className = "text-danger mt-2 fw-bold";
                err.innerText = data.message;
                form.appendChild(err);
            }
        })
        .catch(() => {
            const err = document.createElement("div");
            err.className = "text-danger mt-2 fw-bold";
            err.innerText = "خطا در ارسال. دوباره تلاش کنید.";
            form.appendChild(err);
        });

    });

});

// --- Like / Dislike ---
document.querySelectorAll(".like-btn, .dislike-btn").forEach(btn => {
    btn.addEventListener("click", function (e) {
        e.preventDefault();

        const content_type_id = this.dataset.type;
        const object_id = this.dataset.id;
        const value = this.dataset.value;

        fetch("/core/vote/", {
            method: "POST",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
            },
            body: new URLSearchParams({
                content_type_id,
                object_id,
                value
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === "success") {
                const parent = this.closest(".d-flex");
                const likeBtn = parent.querySelector(".like-btn i");
                const dislikeBtn = parent.querySelector(".dislike-btn i");
                const likeCount = parent.querySelector(".like-count");
                const dislikeCount = parent.querySelector(".dislike-count");

                // --- بروزرسانی شمارنده‌ها
                likeCount.textContent = data.likes;
                dislikeCount.textContent = data.dislikes;

                // --- ریست کلاس‌ها روی آیکون‌ها
                likeBtn.className = "bi vote-icon bi-hand-thumbs-up";
                dislikeBtn.className = "bi vote-icon bi-hand-thumbs-down";

                // --- اگر کاربر لایک یا دیس‌لایک کرده
                if (data.action === "created" || data.action === "updated") {
                    if (value === "1") {
                        likeBtn.className = "bi vote-icon vote-filled bi-hand-thumbs-up-fill";
                    } else if (value === "-1") {
                        dislikeBtn.className = "bi vote-icon vote-filled bi-hand-thumbs-down-fill";
                    }
                }
            } else {
                alert(data.message);
            }
        })
        .catch(() => alert("خطا در ثبت رأی"));
    });
});