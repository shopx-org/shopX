const csrfToken = "{{ csrf_token }}";

    function showAlert(message, type = "success") {
        const html = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="close" data-dismiss="alert">
                    <span>&times;</span>
                </button>
            </div>`;
        document.getElementById('alert-area').innerHTML = html;
    }

    async function postData(data) {
        const response = await fetch("{% url 'dashboards:change_phone_otp' %}", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "X-CSRFToken": csrfToken
            },
            body: new URLSearchParams(data)
        });
        return response.json();
    }

    // مرحله ۱
    document.getElementById('send_otp_old').onclick = async () => {
        const newPhone = document.querySelector('[name="new_phone"]').value.trim();
        if (!newPhone) return showAlert("لطفاً شماره جدید را وارد کنید.", "danger");

        const res = await postData({ stage: "send_old", new_phone: newPhone });
        showAlert(res.message, res.status === "ok" ? "success" : "danger");

        if (res.status === "ok") {
            document.getElementById('step-new-phone').style.display = 'none';
            document.getElementById('step-verify-old').style.display = 'block';
        }
    };

    // مرحله ۲
    document.getElementById('verify_old').onclick = async () => {
        const code = document.getElementById('otp_old').value.trim();
        const newPhone = document.querySelector('[name="new_phone"]').value.trim();
        if (!code) return showAlert("کد تأیید را وارد کنید.", "danger");

        const res = await postData({ stage: "verify_old", code, new_phone: newPhone });
        showAlert(res.message, res.status === "ok" ? "success" : "danger");

        if (res.status === "ok") {
            document.getElementById('step-verify-old').style.display = 'none';
            document.getElementById('step-verify-new').style.display = 'block';
        }
    };

    // مرحله ۳
    document.getElementById('verify_new').onclick = async () => {
        const code = document.getElementById('otp_new').value.trim();
        const newPhone = document.querySelector('[name="new_phone"]').value.trim();
        if (!code) return showAlert("کد تأیید شماره جدید را وارد کنید.", "danger");

        const res = await postData({ stage: "verify_new", code, new_phone: newPhone });
        showAlert(res.message, res.status === "done" ? "success" : "danger");

        if (res.status === "done") {
            setTimeout(() => window.location.reload(), 2000);
        }
    };