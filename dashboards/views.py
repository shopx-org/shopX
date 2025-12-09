# /home/atusa92/PycharmProjects/ShopX/dashboards/views.py
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, datetime
from .forms import DashboardAccountForm, ChangePhoneNumberForm
from OTP_app import services as otp_services
from Core.models import Comment
from orders.models import Order
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin



User = get_user_model()


@method_decorator(login_required, name='dispatch')
class DashboardView(View):
    def get(self, request):
        return render(request, 'dashboards/dashboard.html', {'message': 'خوش آمدید به داشبورد!'})


@method_decorator(login_required, name='dispatch')
class PersonalInfoView(View):
    template_name = 'dashboards/personal_info.html'

    def get(self, request):
        form = DashboardAccountForm(instance=request.user, user=request.user)
        return render(request, self.template_name, {'form': form, 'phone': request.user.phone})

    def post(self, request):
        form = DashboardAccountForm(request.POST, instance=request.user, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'اطلاعات با موفقیت ذخیره شد.')
            if form.cleaned_data.get('new_password'):
                messages.success(request, 'رمز عبور تغییر کرد. لطفاً دوباره وارد شوید.')
                return redirect('account:logout')
            return redirect('dashboards:personal_info')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label}: {error}")
        return render(request, self.template_name, {'form': form})


# ==========================
# 🔹 تغییر شماره موبایل با OTP
# ==========================
@method_decorator(login_required, name='dispatch')
class ChangePhoneOtpView(View):
    template_name = 'dashboards/change_phone_number.html'

    def get(self, request):
        form = ChangePhoneNumberForm(user=request.user)
        return render(request, self.template_name, {'form': form, 'phone': request.user.phone})

    def post(self, request):
        stage = request.POST.get('stage')       # send_old | verify_old | verify_new
        code = request.POST.get('code')
        new_phone = request.POST.get('new_phone', '').strip()
        token = request.POST.get('token')
        sess = request.session

        try:
            # === مرحله ۱: ارسال کد به شماره فعلی ===
            if stage == 'send_old':
                # 🔸 اجرای فرم ولیدیشن قبل از ارسال OTP
                form = ChangePhoneNumberForm({'new_phone': new_phone}, user=request.user)
                if not form.is_valid():
                    # ارسال خطای فارسی از فرم به JSON
                    error_msg = next(iter(form.errors.values()))[0]
                    return JsonResponse({'status': 'error', 'message': error_msg})

                # حالا که معتبره، شماره‌ی تمیزشده را بگیریم
                new_phone = form.cleaned_data['new_phone']

                now = timezone.now()
                last = sess.get('otp_last_sent')

                # محدودیت ۶۰ ثانیه‌ای برای ارسال مجدد
                if last and last.get('phone') == request.user.phone:
                    last_ts = datetime.fromisoformat(last.get('ts'))
                    if (now - last_ts) < timedelta(seconds=60):
                        return JsonResponse({
                            'status': 'ok',
                            'token': last.get('token'),
                            'stage': 'verify_old',
                            'message': 'کد قبلاً ارسال شده است، لطفاً صبر کنید یا کد را وارد کنید.'
                        })

                # ✅ حالا مجاز است OTP ارسال شود
                token = otp_services.create_session(request.user.phone)
                sess['otp_last_sent'] = {'phone': request.user.phone, 'ts': now.isoformat(), 'token': token}
                sess['otp_pending_new_phone'] = new_phone
                sess.modified = True

                return JsonResponse({
                    'status': 'ok',
                    'token': token,
                    'stage': 'verify_old',
                    'message': 'کد تأیید برای شماره فعلی ارسال شد.'
                })

            # === مرحله ۲: تأیید شماره فعلی و ارسال کد به شماره جدید ===
            elif stage == 'verify_old':
                token_in = token or sess.get('otp_last_sent', {}).get('token')
                if not token_in:
                    return JsonResponse({'status': 'error', 'message': 'کد تأیید معتبر یافت نشد.'})

                otp_services.verify(token_in, code)

                pending_new = new_phone or sess.get('otp_pending_new_phone')
                if not pending_new:
                    return JsonResponse({'status': 'error', 'message': 'شماره جدید مشخص نیست.'})
                if User.objects.filter(phone=pending_new).exists():
                    return JsonResponse({'status': 'error', 'message': 'شماره جدید قبلاً ثبت شده است.'})

                now = timezone.now()
                last = sess.get('otp_last_sent_new', {})
                if last and last.get('phone') == pending_new:
                    last_ts = datetime.fromisoformat(last.get('ts'))
                    if (now - last_ts) < timedelta(seconds=60):
                        return JsonResponse({
                            'status': 'ok',
                            'token': last.get('token'),
                            'stage': 'verify_new',
                            'message': 'کد برای شماره جدید قبلاً ارسال شده است.'
                        })

                token_new = otp_services.create_session(pending_new)
                sess['otp_last_sent_new'] = {'phone': pending_new, 'ts': now.isoformat(), 'token': token_new}
                sess['otp_pending_new_phone'] = pending_new
                sess.modified = True

                return JsonResponse({
                    'status': 'ok',
                    'token': token_new,
                    'stage': 'verify_new',
                    'message': 'کد دوم برای شماره جدید ارسال شد.'
                })

            # === مرحله ۳: تأیید شماره جدید و ثبت تغییر ===
            elif stage == 'verify_new':
                token_in = token or sess.get('otp_last_sent_new', {}).get('token')
                pending_new = new_phone or sess.get('otp_pending_new_phone')

                if not token_in or not pending_new:
                    return JsonResponse({'status': 'error', 'message': 'اطلاعات تأیید ناقص است.'})

                otp_services.verify(token_in, code)

                if User.objects.filter(phone=pending_new).exists():
                    return JsonResponse({'status': 'error', 'message': 'این شماره در حال حاضر ثبت شده است.'})

                request.user.phone = pending_new
                request.user.save()

                # پاکسازی session پس از موفقیت
                for key in ['otp_last_sent', 'otp_last_sent_new', 'otp_pending_new_phone']:
                    sess.pop(key, None)
                sess.modified = True

                return JsonResponse({'status': 'done', 'message': 'شماره موبایل با موفقیت تغییر یافت.'})

            # مرحله نامعتبر
            return JsonResponse({'status': 'error', 'message': 'درخواست نامعتبر است.'})

        except otp_services.OtpError as e:
            error_str = str(e).lower().strip()
            if 'bad' in error_str or 'invalid' in error_str or 'wrong' in error_str:
                message = 'کد وارد شده اشتباه است.'
            elif 'expire' in error_str or 'expiration' in error_str or 'expired' in error_str:
                message = 'زمان اعتبار کد به پایان رسیده است.'
            else:
                message = str(e)
            return JsonResponse({'status': 'error', 'message': message})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'خطای داخلی سرور: {str(e)}'})
        

@method_decorator(login_required, name='dispatch')
class UserCommentsView(View):
    template_name = 'dashboards/user_comments.html'

    def get(self, request):
        comments = Comment.objects.filter(
            user=request.user
        ).select_related('content_type', 'parent').order_by('-created_at')

        return render(request, self.template_name, {
            'comments': comments,
        })



class DeleteCommentAjaxView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            comment = Comment.objects.get(pk=pk, user=request.user)
            comment.delete()
            return JsonResponse({'status': 'ok'})
        except Comment.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'کامنت پیدا نشد'}, status=404)



@method_decorator(login_required, name='dispatch')
class UserOrdersView(View):
    """
    لیست سفارش‌های کاربر لاگین شده
    """
    template_name = 'dashboards/user_orders.html'

    def get(self, request):
        orders = (
            Order.objects
            .filter(user=request.user)
            .order_by('-created_at')
        )
        return render(request, self.template_name, {
            'orders': orders,
        })


@method_decorator(login_required, name="dispatch")
class UserOrderDetailView(View):
    template_name = "dashboards/user_order_detail.html"

    def get(self, request, pk):
        order = get_object_or_404(
            Order.objects.select_related("address"),
            pk=pk,
            user=request.user,
        )

        # مپ کردن وضعیت ارسال به شماره استپ
        status_to_step = {
            Order.FulfillmentStatus.NEW:        1,  # تازه ثبت شده
            Order.FulfillmentStatus.PROCESSING: 2,  # در حال آماده‌سازی / بسته‌بندی
            Order.FulfillmentStatus.SHIPPED:    3,  # تحویل پیک / پست
            Order.FulfillmentStatus.DELIVERED:  4,  # تحویل مشتری
            Order.FulfillmentStatus.RETURNED:   4,  # فعلاً همون آخر، می‌تونی جدا استایل بدی
            Order.FulfillmentStatus.SEND_CANCELED: 2,  # لغو قبل از ارسال؛ تا استپ آماده‌سازی
        }

        tracking_step = status_to_step.get(order.fulfillment_status, 1)

        return render(request, self.template_name, {
            "order": order,
            "tracking_step": tracking_step,
        })