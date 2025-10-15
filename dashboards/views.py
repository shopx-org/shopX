from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from .forms import DashboardAccountForm
from OTP_app import services as otp_services

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


@method_decorator(login_required, name='dispatch')
class ChangePhoneOtpView(View):
    """
    مدیریت تغییر شماره موبایل دو مرحله‌ای با OTP.
    نکات کلیدی:
    - اگر new_phone قبلاً در DB باشد: هیچ OTP ای ارسال نمی‌شود و پیام خطا برگردانده می‌شود.
    - سرور با session جلوی ارسال مکرر SMS به یک شماره در کمتر از 60 ثانیه را می‌گیرد.
    - پاسخ JSON تمیز و مشخص برمی‌گردد؛ پیام برای نمایش در UI در همان پاسخ موجود است.
    """

    def post(self, request):
        stage = request.POST.get('stage')
        code = request.POST.get('code')
        new_phone = request.POST.get('new_phone')
        token = request.POST.get('token')

        try:
            # ===================
            # مرحله ۱: ارسال برای شماره فعلی (send_old)
            # ===================
            if stage == 'send_old':
                # اگر شماره جدید قبلاً موجود باشد، جلوی ادامه را بگیر
                if new_phone and User.objects.filter(phone=new_phone).exists():
                    return JsonResponse({'status': 'error', 'message': 'یک حساب با این شماره از قبل وجود دارد.'})

                # محافظت سمت سرور: اگر همین شماره طی ۶۰ ثانیه اخیر پیام داشته، دوباره نزن
                sess = request.session
                now = timezone.now()
                last = sess.get('otp_last_sent')  # ساختار: {'phone': '09...', 'ts': 'ISO', 'token': '...'}
                if last and last.get('phone') == request.user.phone:
                    last_ts = timezone.datetime.fromisoformat(last.get('ts'))
                    # اگر کمتر از 60 ثانیه گذشته، برگردون همان توکن (بدون ارسال مجدد)
                    if (now - last_ts) < timedelta(seconds=60):
                        return JsonResponse({
                            'status': 'ok',
                            'token': last.get('token'),
                            'stage': 'verify_old',
                            'message': 'کد قبلاً ارسال شده، لطفاً صبر کنید یا کد را وارد کنید.'
                        })

                # در غیر این صورت بساز و ارسال کن
                token = otp_services.create_session(request.user.phone)
                # ذخیره در session برای جلوگیری از send دوباره
                sess['otp_last_sent'] = {
                    'phone': request.user.phone,
                    'ts': now.isoformat(),
                    'token': token
                }
                # ذخیره موقت شماره جدید (تا بعداً وقتی verify_old آمد بدانیم new_phone چیست)
                sess['otp_pending_new_phone'] = new_phone
                sess.modified = True

                return JsonResponse({
                    'status': 'ok',
                    'token': token,
                    'stage': 'verify_old',
                    'message': 'کد تأیید برای شماره فعلی ارسال شد.'
                })

            # ===================
            # مرحله ۲: تایید شماره فعلی -> ارسال برای شماره جدید (verify_old)
            # ===================
            elif stage == 'verify_old':
                # token ممکن است از session نیز بیاید
                sess = request.session
                token_in = token or sess.get('otp_last_sent', {}).get('token')
                if not token_in:
                    return JsonResponse({'status': 'error', 'message': 'توکن معتبر یافت نشد.'})

                # verify تابع سرویس اصلی
                otp_services.verify(token_in, code)

                # پیش از ارسال به شماره جدید یک بار دیگر چک کن که new_phone هنوز آزاد است
                # (ممکن است در بین ارسال اول و این مرحله، شماره توسط شخص دیگری ثبت شده باشد)
                pending_new = new_phone or sess.get('otp_pending_new_phone')
                if not pending_new:
                    return JsonResponse({'status': 'error', 'message': 'شماره جدید برای ارسال یافت نشد.'})
                if User.objects.filter(phone=pending_new).exists():
                    return JsonResponse({'status': 'error', 'message': 'این شماره قبلاً برای حساب دیگری ثبت شده است.'})

                # محافظت برای شماره جدید (جلوگیری از ارسال مکرر)
                now = timezone.now()
                last = sess.get('otp_last_sent_new', {})
                if last and last.get('phone') == pending_new:
                    last_ts = timezone.datetime.fromisoformat(last.get('ts'))
                    if (now - last_ts) < timedelta(seconds=60):
                        return JsonResponse({
                            'status': 'ok',
                            'token': last.get('token'),
                            'stage': 'verify_new',
                            'message': 'کد برای شماره جدید قبلاً ارسال شده است، لطفاً منتظر بمانید.'
                        })

                # ارسال به شماره جدید
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

            # ===================
            # مرحله ۳: تایید شماره جدید (verify_new)
            # ===================
            elif stage == 'verify_new':
                sess = request.session
                token_in = token or sess.get('otp_last_sent_new', {}).get('token')
                pending_new = new_phone or sess.get('otp_pending_new_phone')

                if not token_in or not pending_new:
                    return JsonResponse({'status': 'error', 'message': 'توکن یا شماره جدید معتبر یافت نشد.'})

                # verify و سپس اعمال تغییر
                otp_services.verify(token_in, code)

                # دوباره چک کن شماره جدید قبلاً ثبت نشده باشد (حالت race)
                if User.objects.filter(phone=pending_new).exists():
                    return JsonResponse({'status': 'error', 'message': 'این شماره قبلاً ثبت شده است.'})

                # ثبت شماره جدید فقط برای کاربر جاری (ایجاد کاربر جدید ندارد)
                user = request.user
                user.phone = pending_new
                user.save()

                # پاکسازی session
                sess.pop('otp_last_sent', None)
                sess.pop('otp_last_sent_new', None)
                sess.pop('otp_pending_new_phone', None)
                sess.modified = True

                return JsonResponse({'status': 'done', 'message': 'شماره موبایل با موفقیت تغییر یافت.'})

            else:
                return JsonResponse({'status': 'error', 'message': 'درخواست نامعتبر است.'})

        except otp_services.OtpError as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': 'خطای داخلی: ' + str(e)})
