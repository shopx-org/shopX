document.addEventListener('DOMContentLoaded', async function () {
    const form = document.getElementById('addressForm');
    const addressIdInput = document.getElementById('address_id');
    const actionInput = form.querySelector('input[name="action"]');
    const saveBtn = form.querySelector('.btn-save');
    const provinceSelect = document.getElementById('id_province');
    const citySelect = document.getElementById('id_city');

    // ========== 1️⃣ بارگذاری شهرها ==========
    let citiesByProvince = {};
    try {
        const res = await fetch('/static/data/iran_cities.json');
        if (res.ok) citiesByProvince = await res.json();
    } catch (err) {
        console.error('خطا در بارگذاری فایل شهرها', err);
    }

    function populateCitySelect(province, selectedCity = '') {
        citySelect.innerHTML = '';
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'لطفاً شهر را انتخاب کنید';
        citySelect.appendChild(defaultOption);

        if (province && citiesByProvince[province]) {
            const sortedCities = [...citiesByProvince[province]].sort((a, b) => a.localeCompare(b, 'fa'));
            sortedCities.forEach(city => {
                const opt = document.createElement('option');
                opt.value = city;
                opt.textContent = city;
                if (city === selectedCity) opt.selected = true;
                citySelect.appendChild(opt);
            });
        }
    }

    provinceSelect?.addEventListener('change', function () {
        populateCitySelect(this.value.trim());
    });

    // ========== 2️⃣ دکمه حذف ==========
    const deleteButtons = document.querySelectorAll('.btn-delete');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', function () {
            const card = this.closest('.address-card');
            const addrId = card.dataset.id;
            if (confirm('آیا از حذف این آدرس اطمینان دارید؟')) {
                actionInput.value = 'delete';
                addressIdInput.value = addrId;
                form.submit();
            }
        });
    });

    // ========== 3️⃣ ویرایش ==========
    const editButtons = document.querySelectorAll('.btn-edit');
    editButtons.forEach(btn => {
        btn.addEventListener('click', function () {
            const card = this.closest('.address-card');
            addressIdInput.value = card.dataset.id;
            actionInput.value = 'update';

            document.getElementById('id_title').value = card.dataset.title || '';
            document.getElementById('id_province').value = card.dataset.province || '';
            populateCitySelect(card.dataset.province || '', card.dataset.city || '');
            document.getElementById('id_address').value = card.dataset.address || '';
            document.getElementById('id_number').value = card.dataset.number || '';
            document.getElementById('id_unit').value = card.dataset.unit || '';
            document.getElementById('id_postal_code').value = card.dataset.postal_code || '';
            document.getElementById('latitude').value = card.dataset.latitude || '';
            document.getElementById('longitude').value = card.dataset.longitude || '';
            document.getElementById('id_is_default').checked = (card.dataset.is_default === 'True');

            saveBtn.innerHTML = '<i class="fas fa-save ms-2"></i> ذخیره تغییرات آدرس';
            saveBtn.classList.add('btn-warning');

            form.classList.add('active');

            setTimeout(() => {
                const y = form.getBoundingClientRect().top + window.pageYOffset - 100;
                window.scrollTo({top: y, behavior: 'smooth'});
                document.getElementById('id_title').focus();
            }, 200);
        });
    });

    // ========== 4️⃣ افزودن آدرس جدید ==========
    const btnAdd = document.getElementById('btnAddAddress');
    if (btnAdd) {
        btnAdd.addEventListener('click', function () {
            form.reset();
            addressIdInput.value = '';
            actionInput.value = 'add';
            saveBtn.innerHTML = '<i class="fas fa-save ms-2"></i> ذخیره آدرس جدید';
            saveBtn.classList.remove('btn-warning');
            form.classList.add('active');
            setTimeout(() => {
                const y = form.getBoundingClientRect().top + window.pageYOffset - 100;
                window.scrollTo({top: y, behavior: 'smooth'});
                document.getElementById('id_title').focus();
            }, 200);
        });
    }

    // ========== 5️⃣ انتخاب آدرس پیش‌فرض ==========
    const addressCards = document.querySelectorAll('.address-card');
    addressCards.forEach(card => {
        card.addEventListener('click', async function (e) {
            if (e.target.closest('.btn-edit') || e.target.closest('.btn-delete')) return;

            const selectedId = this.dataset.id;
            addressCards.forEach(c => c.classList.remove('selected'));
            this.classList.add('selected');

            // نمایش فوری در UI
            document.querySelectorAll('.badge.bg-success').forEach(b => b.remove());
            const badgeContainer = this.querySelector('.text-right');
            const newBadge = document.createElement('span');
            newBadge.className = 'badge bg-success';
            newBadge.innerText = 'پیش‌فرض';
            badgeContainer.appendChild(newBadge);

            // ارسال درخواست به سرور
            try {
                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
                console.log('setDefaultAddressURL =', setDefaultAddressURL);

                const response = await fetch(setDefaultAddressURL, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken,
                    },
                    body: JSON.stringify({address_id: selectedId}),
                });

                const data = await response.json();
                if (!response.ok || !data.success) {
                    console.log('DEBUG set-default:', response.status, data);
                    alert(data.error || 'خطا در تغییر آدرس پیش‌فرض');
                }

            } catch (err) {
                console.error('❌ خطا در ارتباط با سرور:', err);
                alert('ارتباط با سرور برقرار نشد');
            }
        });
    });
});

