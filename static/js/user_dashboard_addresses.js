document.addEventListener('DOMContentLoaded', async function () {
  const provinceSelect = document.getElementById('id_province');
  const citySelect = document.getElementById('id_city');
  const form = document.getElementById('addressForm');
  const addressIdInput = document.getElementById('address_id');
  const actionInput = form.querySelector('input[name="action"]');
  const saveBtn = form.querySelector('.btn-save');

  // ======== 1️⃣ خواندن شهرها از فایل JSON ======== //
  let citiesByProvince = {};
  try {
    const response = await fetch('/static/data/iran_cities.json');
    if (response.ok) {
      citiesByProvince = await response.json();
    } else {
      console.error('خطا در بارگذاری فایل iran_cities.json');
    }
  } catch (err) {
    console.error('عدم دسترسی به فایل iran_cities.json', err);
  }

  if (!provinceSelect || !citySelect) return;

  function populateCitySelect(province, selectedCity = '') {
    citySelect.innerHTML = '';
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = 'لطفاً شهر را انتخاب کنید';
    citySelect.appendChild(defaultOption);

    if (province && citiesByProvince[province]) {
      const sortedCities = [...citiesByProvince[province]].sort((a, b) =>
        a.localeCompare(b, 'fa')
      );
      sortedCities.forEach(city => {
        const opt = document.createElement('option');
        opt.value = city;
        opt.textContent = city;
        if (city === selectedCity) opt.selected = true;
        citySelect.appendChild(opt);
      });
    }
  }

  provinceSelect.addEventListener('change', function () {
    populateCitySelect(this.value.trim());
  });

  // مقدار اولیه فرم (برای حالت ویرایش از سمت سرور)
  const initialProvince = "{{ form.province.value|default_if_none:''|escapejs }}";
  const initialCity = "{{ form.city.value|default_if_none:''|escapejs }}";
  if (initialProvince) {
    populateCitySelect(initialProvince, initialCity);
  }

  // ======== 2️⃣ حذف آدرس ======== //
  const deleteButtons = document.querySelectorAll('.btn-delete');
  deleteButtons.forEach(btn => {
    btn.addEventListener('click', function () {
      const card = this.closest('.address-card');
      const addrId = card.dataset.id;

      if (confirm('آیا از حذف این آدرس اطمینان دارید؟')) {
        actionInput.value = 'delete';
        addressIdInput.value = addrId;
        form.submit(); // ارسال فرم به view
      }
    });
  });

// ======== 3️⃣ ویرایش آدرس ======== //
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

    // نمایش فرم
    const form = document.getElementById('addressForm');
    form.classList.add('active');

    // اسکرول نرم به بالای فرم
    setTimeout(() => {
      const y = form.getBoundingClientRect().top + window.pageYOffset - 100;
      window.scrollTo({ top: y, behavior: 'smooth' });
      document.getElementById('id_title').focus();
    }, 200);
  });
});


  // ======== 4️⃣ بازگردانی فرم به حالت افزودن ======== //
  form.addEventListener('submit', function () {
    actionInput.value = 'add';
    saveBtn.innerHTML = '<i class="fas fa-save ms-2"></i> ذخیره آدرس جدید';
    saveBtn.classList.remove('btn-warning');
  });

  // ======== 5️⃣ نمایش فرم افزودن آدرس جدید ======== //
  const btnAdd = document.getElementById('btnAddAddress');
  if (btnAdd) {
    btnAdd.addEventListener('click', function () {
      const form = document.getElementById('addressForm');
      form.reset(); // پاک کردن مقادیر قبلی
      addressIdInput.value = '';
      actionInput.value = 'add';
      saveBtn.innerHTML = '<i class="fas fa-save ms-2"></i> ذخیره آدرس جدید';
      saveBtn.classList.remove('btn-warning');

      // نمایش فرم
      form.classList.add('active');

      // اسکرول نرم به بالای فرم
      setTimeout(() => {
        const y = form.getBoundingClientRect().top + window.pageYOffset - 100;
        window.scrollTo({ top: y, behavior: 'smooth' });
        document.getElementById('id_title').focus();
      }, 200);
    });
  }
});

  // ======== 6️⃣ انتخاب آدرس به عنوان پیش‌فرض ======== //
  const addressCards = document.querySelectorAll('.address-card');
  addressCards.forEach(card => {
    card.addEventListener('click', async function (e) {
      // جلوگیری از تداخل با دکمه‌های ویرایش و حذف
      if (e.target.closest('.btn-edit') || e.target.closest('.btn-delete')) return;

      const selectedId = this.dataset.id;

      // حذف حالت انتخاب از همه‌ی کارت‌ها
      addressCards.forEach(c => c.classList.remove('selected'));
      this.classList.add('selected');

      // نمایش فوری تغییر در رابط کاربری
      const badge = this.querySelector('.badge');
      document.querySelectorAll('.badge.bg-success').forEach(b => b.remove());
      const newBadge = document.createElement('span');
      newBadge.className = 'badge bg-success';
      newBadge.innerText = 'پیش‌فرض';
      badge?.remove();
      this.querySelector('.text-right').appendChild(newBadge);

      // درخواست به سرور برای ذخیره پیش‌فرض جدید
      try {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        const response = await fetch('{% url "shipping:set_default_address" %}', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({ address_id: selectedId })
        });

        if (!response.ok) {
          alert('خطا در تغییر آدرس پیش‌فرض');
        }
      } catch (err) {
        console.error('خطا در ارتباط با سرور', err);
      }
    });
  });