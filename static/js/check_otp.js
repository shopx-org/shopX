// otp.js
const inputs = document.querySelectorAll('.otp-input');
const hiddenInput = document.getElementById('otpCode');
const form = document.getElementById('otpForm');

inputs.forEach((input, index) => {
    input.addEventListener('input', () => {
        if (input.value.length === 1 && index < inputs.length - 1) {
            inputs[index + 1].focus();
        }
    });
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Backspace' && input.value.length === 0 && index > 0) {
            inputs[index - 1].focus();
        }
    });
});

form.addEventListener('submit', () => {
    let code = '';
    inputs.forEach(input => code += input.value);
    hiddenInput.value = code; });