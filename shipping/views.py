# shipping/views.py
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .forms import AddressForm
from .models import Address
from django.views.decorators.csrf import csrf_exempt
import json

@method_decorator(login_required, name='dispatch')
class AddressesView(View):
    template_name = 'dashboards/addresses.html'

    def get(self, request):
        addresses = request.user.addresses.all()
        form = AddressForm()
        return render(request, self.template_name, {'addresses': addresses, 'form': form})

    def post(self, request):
        action = request.POST.get('action')
        address_id = request.POST.get('address_id')

    # حذف آدرس
        if action == 'delete':
            try:
                address = Address.objects.get(id=address_id, user=request.user)
                address.delete()
                messages.success(request, 'آدرس با موفقیت حذف شد.')
            except Address.DoesNotExist:
                messages.error(request, 'آدرس مورد نظر یافت نشد.')
            return redirect('dashboards:addresses')

        # افزودن یا ویرایش آدرس
        if address_id and action in ['update', 'add']:
            address = get_object_or_404(Address, id=address_id, user=request.user)
            form = AddressForm(request.POST, instance=address)
        else:
            form = AddressForm(request.POST)

        if form.is_valid():
            form.save(user=request.user)
            messages.success(request, 'آدرس با موفقیت ذخیره شد.')
            return redirect('dashboards:addresses')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label}: {error}")
            addresses = request.user.addresses.all()
            return render(request, self.template_name, {'addresses': addresses, 'form': form})
        

# ===========================================================
# 🔹 تابع API برای انتخاب آدرس پیش‌فرض
# ===========================================================
@login_required
def set_default_address(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            addr_id = data.get("address_id")
            if not addr_id:
                return JsonResponse({"error": "شناسه آدرس نامعتبر است"}, status=400)

            # ریست آدرس‌های پیش‌فرض کاربر
            Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
            # تنظیم آدرس جدید به‌عنوان پیش‌فرض
            Address.objects.filter(id=addr_id, user=request.user).update(is_default=True)

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "درخواست نامعتبر"}, status=400)