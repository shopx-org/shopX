function toggleWishlist(button) {
    const productId = button.dataset.productId;
    const url = button.dataset.toggleUrl;
    const csrfToken = button.dataset.csrfToken;
    const icon = button.querySelector("i");

    fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken
        },
        body: JSON.stringify({ product_id: productId })
    })
    .then(res => res.json())
    .then(data => {

        const span = button.querySelector("span");

        if (data.status === "added") {
            icon.classList.replace("bi-heart", "bi-heart-fill");
            span.textContent = " حذف از علاقه‌مندی‌ها";
        } else {
            icon.classList.replace("bi-heart-fill", "bi-heart");
            span.textContent = " افزودن به لیست علاقه‌مندی";
        }

        // آپدیت عدد نوبار
        const badge = document.querySelector(".wishlist-count");
        if (badge) {
            badge.textContent = data.count;
        }
    });
}

