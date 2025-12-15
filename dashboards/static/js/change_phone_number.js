'use strict';

const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
const alertArea = document.getElementById('alert-area');

function showAlert(message, type = 'success') {
    alertArea.className = `alert alert-${type}`;
    alertArea.textContent = message;
}

async function postData(payload) {
    const res = await fetch('/dashboards/change-phone-otp/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: new URLSearchParams(payload)
    });
    return res.json();
}

// STEP 1
document.getElementById('sendOtp').addEventListener('click', async () => {
    const phone = document.querySelector('[name="new_phone"]').value.trim();
    if (!phone) return showAlert('شماره جدید را وارد کنید', 'danger');

    const res = await postData({ stage: 'send_old', new_phone: phone });
    showAlert(res.message, res.status === 'ok' ? 'success' : 'danger');

    if (res.status === 'ok') {
        document.getElementById('step-new-phone').hidden = true;
        document.getElementById('step-old').hidden = false;
    }
});

// STEP 2
document.getElementById('verifyOld').addEventListener('click', async () => {
    const code = document.getElementById('otpOld').value.trim();
    if (!code) return showAlert('کد را وارد کنید', 'danger');

    const res = await postData({ stage: 'verify_old', code });
    showAlert(res.message, res.status === 'ok' ? 'success' : 'danger');

    if (res.status === 'ok') {
        document.getElementById('step-old').hidden = true;
        document.getElementById('step-new').hidden = false;
    }
});

// STEP 3
document.getElementById('verifyNew').addEventListener('click', async () => {
    const code = document.getElementById('otpNew').value.trim();
    if (!code) return showAlert('کد جدید را وارد کنید', 'danger');

    const res = await postData({ stage: 'verify_new', code });
    showAlert(res.message, res.status === 'done' ? 'success' : 'danger');

    if (res.status === 'done') {
        setTimeout(() => location.reload(), 1500);
    }
});



// const csrfToken = "{{ csrf_token }}";

//     function showAlert(message, type = "success") {
//         const html = `
//             <div class="alert alert-${type} alert-dismissible fade show" role="alert">
//                 ${message}
//                 <button type="button" class="close" data-dismiss="alert">
//                     <span>&times;</span>
//                 </button>
//             </div>`;
//         document.getElementById('alert-area').innerHTML = html;
//     }

//     async function postData(data) {
//         const response = await fetch("{% url 'dashboards:change_phone_otp' %}", {
//             method: "POST",
//             headers: {
//                 "Content-Type": "application/x-www-form-urlencoded",
//                 "X-CSRFToken": csrfToken
//             },
//             body: new URLSearchParams(data)
//         });
//         return response.json();
//     }

//     // مرحله ۱
//     document.getElementById('send_otp_old').onclick = async () => {
//         const newPhone = document.querySelector('[name="new_phone"]').value.trim();
//         if (!newPhone) return showAlert("لطفاً شماره جدید را وارد کنید.", "danger");

//         const res = await postData({ stage: "send_old", new_phone: newPhone });
//         showAlert(res.message, res.status === "ok" ? "success" : "danger");

//         if (res.status === "ok") {
//             document.getElementById('step-new-phone').style.display = 'none';
//             document.getElementById('step-verify-old').style.display = 'block';
//         }
//     };

//     // مرحله ۲
//     document.getElementById('verify_old').onclick = async () => {
//         const code = document.getElementById('otp_old').value.trim();
//         const newPhone = document.querySelector('[name="new_phone"]').value.trim();
//         if (!code) return showAlert("کد تأیید را وارد کنید.", "danger");

//         const res = await postData({ stage: "verify_old", code, new_phone: newPhone });
//         showAlert(res.message, res.status === "ok" ? "success" : "danger");

//         if (res.status === "ok") {
//             document.getElementById('step-verify-old').style.display = 'none';
//             document.getElementById('step-verify-new').style.display = 'block';
//         }
//     };

//     // مرحله ۳
//     document.getElementById('verify_new').onclick = async () => {
//         const code = document.getElementById('otp_new').value.trim();
//         const newPhone = document.querySelector('[name="new_phone"]').value.trim();
//         if (!code) return showAlert("کد تأیید شماره جدید را وارد کنید.", "danger");

//         const res = await postData({ stage: "verify_new", code, new_phone: newPhone });
//         showAlert(res.message, res.status === "done" ? "success" : "danger");

//         if (res.status === "done") {
//             setTimeout(() => window.location.reload(), 2000);
//         }
//     };