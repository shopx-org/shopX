# shipping/views.py
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from django.shortcuts import get_object_or_404
from .forms import AddressForm
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse, HttpRequest
from decimal import Decimal
from django.views.decorators.http import require_POST
from django.conf import settings
from cart.cart import Cart
from .models import Address, ShippingMethod


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
@require_POST
@login_required
def set_default_address(request: HttpRequest) -> JsonResponse:
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        payload = {}

    addr_id = int(payload.get("address_id") or 0)
    if not addr_id:
        return JsonResponse({"success": False, "error": "bad-id"}, status=400)

    try:
        addr = Address.objects.get(pk=addr_id, user=request.user)
    except Address.DoesNotExist:
        return JsonResponse({"success": False, "error": "not-found"}, status=404)

    Address.objects.filter(user=request.user, is_default=True)\
                   .exclude(pk=addr.pk)\
                   .update(is_default=False)

    if not addr.is_default:
        addr.is_default = True
        addr.save(update_fields=["is_default"])

    request.session["checkout.address_id"] = addr.id

    return JsonResponse({"success": True, "address_id": addr.id})

#
#
# @require_POST
# @login_required
# def ajax_shipping_quote(request: HttpRequest) -> JsonResponse:
#     """
#     ایجکس برای محاسبه هزینه ارسال بر اساس:
#       - سبد خرید فعلی
#       - آدرس انتخاب‌شده
#       - روش ارسال انتخاب‌شده
#     """
#
#     # 1) سبد خرید
#     cart = Cart(request)
#     items = list(cart.items())
#     if not items:
#         return JsonResponse({"ok": False, "error": "empty-cart"}, status=400)
#
#     # 2) body
#     try:
#         payload = json.loads(request.body.decode("utf-8") or "{}")
#     except Exception:
#         payload = {}
#
#     raw_method_id = payload.get("shipping_method_id") or payload.get("method_id")
#     try:
#         method_id = int(raw_method_id)
#     except (TypeError, ValueError):
#         method_id = None
#
#     if not method_id:
#         return JsonResponse({"ok": False, "error": "no-method"}, status=400)
#
#     method = ShippingMethod.objects.filter(pk=method_id, is_active=True).first()
#     if not method:
#         return JsonResponse({"ok": False, "error": "invalid-method"}, status=400)
#
#     # 3) آدرس مقصد (از سشن چک‌اوت)
#     addr_id = request.session.get("checkout.address_id")
#     if not addr_id:
#         addr = Address.objects.filter(user=request.user, is_default=True).first()
#     else:
#         addr = Address.objects.filter(user=request.user, pk=addr_id).first()
#
#     if not addr:
#         return JsonResponse({"ok": False, "error": "no-address"}, status=400)
#
#     if not addr.tapin_province_id or not addr.tapin_city_id:
#         return JsonResponse({"ok": False, "error": "address-missing-tapin-ids"}, status=400)
#
#     # 4) تبدیل Cart به ساختار مورد انتظار tapin_client
#     tapin_cart = []
#     for it in items:
#         qty = getattr(it, "qty", 1) or 1
#         product_obj = getattr(it, "variant", None) or getattr(it, "product", None)
#
#         # وزن بر حسب گرم – اگر نداشت، یه مقدار پیش‌فرض بذار
#         weight_gram = getattr(product_obj, "shipping_weight_grams", None)
#         if weight_gram is None:
#             weight_gram = 500  # مثلا ۵۰۰ گرم پیش‌فرض
#         try:
#             weight_gram = int(weight_gram)
#         except (TypeError, ValueError):
#             weight_gram = 500
#
#         # قیمت واحد به تومان
#         unit_price = getattr(it, "unit_price", None)
#         if unit_price is None:
#             unit_price = 0
#         unit_price = Decimal(str(unit_price))
#
#         tapin_cart.append({
#             "quantity": qty,
#             "weight_gram": weight_gram,
#             "unit_price": unit_price,
#         })
#
#     # 5) صدا زدن API تاپین
#     shipping_amount_toman = Decimal("0")
#
#     try:
#         if method.carrier == "post":
#             # خروجی توی tapin_client به "ریال" است
#             total_rial = tapin_post_check_price(
#                 cart=tapin_cart,
#                 shipping_address=addr,
#                 method=method,
#             )
#             shipping_amount_toman = Decimal(int(total_rial)) / Decimal("10")
#
#         elif method.carrier == "tipax":
#             total_rial = tapin_tipax_check_price(
#                 cart=tapin_cart,
#                 shipping_address=addr,
#                 method=method,
#             )
#             shipping_amount_toman = Decimal(int(total_rial)) / Decimal("10")
#
#         else:
#             # برای روش‌های دیگر (پیک، سفارشی و...) فعلاً فقط base_fee
#             shipping_amount_toman = method.base_fee or Decimal("0")
#
#     except TapinPostError as e:
#         return JsonResponse({"ok": False, "error": f"tapin-post-error: {e}"}, status=400)
#     except TapinTipaxError as e:
#         return JsonResponse({"ok": False, "error": f"tapin-tipax-error: {e}"}, status=400)
#     except Exception as e:
#         return JsonResponse({"ok": False, "error": f"tapin-exception: {e}"}, status=500)
#
#     # 6) اضافه کردن base_fee از خود ShippingMethod (اگر خواستی)
#     base_fee = method.base_fee or Decimal("0")
#     shipping_amount_toman = shipping_amount_toman + base_fee
#
#     request.session["checkout.shipping_method"] = method.id  # کلید جدید برای شناسه روش ارسال
#     request.session["checkout.shipping_method_id"] = method.id  # حفظ کلید قدیمی برای سازگاری
#
#     request.session["checkout.shipping_cost_toman"] = str(shipping_amount_toman)  # کلید جدید (تومان به‌صورت رشته)
#     request.session["checkout.shipping_cost"] = int(shipping_amount_toman)  # حفظ کلید قدیمی (تومان به‌صورت عدد)
#
#
#     return JsonResponse(
#         {
#             "ok": True,
#             "shipping_method_id": method.id,
#             "shipping_name": method.name,
#             "shipping_amount": int(shipping_amount_toman),  # به تومان
#         }
#     )
