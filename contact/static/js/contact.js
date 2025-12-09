document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector(".contact-form");
    const msgBox = document.getElementById("ajax-message");

    form.addEventListener("submit", function (e) {
        e.preventDefault();
        msgBox.innerHTML = "";
        const formData = new FormData(form);

        fetch("", {
            method: "POST",
            headers: {"X-Requested-With": "XMLHttpRequest"},
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                msgBox.innerHTML = `<div class="alert alert-success">${data.message} ✅</div>`;
                form.reset();
                setTimeout(() => { msgBox.innerHTML = ""; }, 4000);
            } else {
                let html = `<div class="alert alert-danger">`;
                if (data.errors["__all__"]) {
                    html += `<div>${data.errors["__all__"][0]}</div>`;
                }
                for (let field in data.errors) {
                    if (field !== "__all__") {
                        data.errors[field].forEach(err => html += `<div>${err}</div>`);
                    }
                }
                html += `</div>`;
                msgBox.innerHTML = html;
            }
        })
        .catch(() => {
            msgBox.innerHTML = `<div class="alert alert-danger">خطایی رخ داد. لطفاً دوباره تلاش کنید.</div>`;
        });
    });
});