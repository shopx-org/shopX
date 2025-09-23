#
# from django.shortcuts import render, redirect, reverse
#
# from django.contrib.auth import authenticate, login, logout
# from django.utils import timezone
# from django_ratelimit.decorators import ratelimit
# from .forms import *
# from django.conf import settings
# from django.utils.decorators import method_decorator
# from django.views import View
# from django.contrib import messages
# from .forms import PasswordOnlyForm
# from .models import User
# from django.core.cache import cache
# from django.contrib.sessions.models import Session
# from django.contrib.auth import get_user_model
# from .forms import SetPasswordForm
# # سرویس‌های اپ otp
# from OTP_app import services as otp_service
# from OTP_app.services import OtpBlocked, OtpTooSoon, OtpMaxReached, OtpInvalid, OtpExpired, OtpError
# from OTP_app.models import OtpSession  # فقط برای نمایش شماره در صفحهٔ check (UI)
#
# User = get_user_model()
#
# # نرخ‌ها بر اساس محیط
# if settings.DEBUG:
#     RATE_IP = "20/m"      # محیط dev
#     RATE_PHONE = "50/m"
# else:
#     RATE_IP = "5/m"       # محیط production
#     RATE_PHONE = "10/m"
#
#
#
# # --- ریت‌لیمیت سبکِ بدون پکیج (cache-based) ---
# def rate_limited(key: str, limit: int, window_seconds: int) -> bool:
#     now = timezone.now().timestamp()
#     data = cache.get(key)
#     if not data:
#         cache.set(key, {"count": 1, "start": now}, timeout=window_seconds)
#         return False
#     count = data["count"]; start = data["start"]
#     if now - start > window_seconds:
#         cache.set(key, {"count": 1, "start": now}, timeout=window_seconds)
#         return False
#     if count + 1 > limit:
#         cache.set(key, {"count": count + 1, "start": start}, timeout=int(window_seconds - (now - start)))
#         return True
#     cache.set(key, {"count": count + 1, "start": start}, timeout=int(window_seconds - (now - start)))
#     return False
#
#
# class ForgotPasswordView(View):
#     template_name = 'account/forgot_password.html'
#
#     def get(self, request):
#         return render(request, self.template_name, {"form": ForgotPasswordForm()})
#
#     def post(self, request):
#         ip = request.META.get("REMOTE_ADDR", "unknown")
#         # ریت‌لیمیت: حداکثر 5 درخواست در 3 دقیقه از این IP
#         if rate_limited(f"rl:forgot:ip:{ip}", limit=5, window_seconds=180):
#             messages.error(request, "تلاش‌های زیاد. کمی بعد دوباره تلاش کنید.")
#             return render(request, self.template_name, {"form": ForgotPasswordForm()})
#
#         form = ForgotPasswordForm(request.POST)
#         if not form.is_valid():
#             return render(request, self.template_name, {"form": form})
#
#         phone = form.cleaned_data["phone"].strip()
#
#         # ضد-enumeration (اختیاری): می‌تونی به‌جای چک وجود کاربر، همیشه پیام «اگر شماره معتبر باشد کد ارسال می‌شود» بدهی
#         if not User.objects.filter(phone=phone).exists():
#             # نسخه واضح (پیام روشن):
#             messages.error(request, "کاربری با این شماره یافت نشد.")
#             return render(request, self.template_name, {"form": form})
#             # نسخه ضد-enum (اگر خواستی):
#             # messages.success(request, "اگر شماره معتبر باشد، کد تایید ارسال خواهد شد.")
#             # return render(request, self.template_name, {"form": ForgotPasswordForm()})
#
#         try:
#             token = otp_service.create_session(phone)
#         except OtpBlocked:
#             messages.error(request, "به دلیل تعدد تلاش‌ها تا یک ساعت امکان ارسال کد ندارید.")
#             return render(request, self.template_name, {"form": form})
#         except OtpTooSoon:
#             messages.error(request, "لطفاً کمی بعد دوباره تلاش کنید.")
#             return render(request, self.template_name, {"form": form})
#         except OtpError:
#             messages.error(request, "ارسال کد با مشکل مواجه شد.")
#             return render(request, self.template_name, {"form": form})
#
#         request.session['reset_phone'] = phone
#         return redirect(reverse('account:reset_verify') + f"?token={token}")
#
#
# class ResetVerifyOtpView(View):
#     template_name = 'account/reset_verify_otp.html'
#
#     def get(self, request):
#         token = request.GET.get('token')
#         phone = None
#         if token:
#             sess = OtpSession.objects.filter(token=token, is_used=False).first()
#             phone = getattr(sess, 'phone', None)
#         return render(request, self.template_name, {
#             'form': CheckOtpForm(),
#             'token': token,
#             'phone': phone,
#             'seconds_left': otp_service.seconds_left(token) if token else 0,
#             'resend_left': otp_service.resends_left(token) if token else 0,
#         })
#
#     def post(self, request):
#         token = request.GET.get('token')
#         if not token:
#             messages.error(request, "درخواست نامعتبر است.")
#             return redirect('account:forgot_password')
#
#         # ریت‌لیمیت تایید OTP: حداکثر 6 تلاش در 5 دقیقه per-ip
#         ip = request.META.get("REMOTE_ADDR", "unknown")
#         if rate_limited(f"rl:resetverify:ip:{ip}", limit=6, window_seconds=300):
#             messages.error(request, "تلاش‌های زیاد. کمی بعد دوباره امتحان کنید.")
#             return redirect(reverse('account:reset_verify') + f"?token={token}")
#
#         # resend
#         if request.POST.get('resend') == '1':
#             try:
#                 otp_service.resend(token)
#                 messages.success(request, "کد جدید ارسال شد.")
#             except OtpBlocked:
#                 messages.error(request, "تا یک ساعت امکان ارسال کد ندارید.")
#                 return redirect('account:forgot_password')
#             except OtpMaxReached:
#                 messages.error(request, "حداکثر ۳ بار ارسال مجدد انجام شد. تا یک ساعت مسدود شدید.")
#                 return redirect('account:forgot_password')
#             except OtpTooSoon:
#                 messages.error(request, "کمی صبر کنید و دوباره تلاش کنید.")
#             except OtpError:
#                 messages.error(request, "ارسال مجدد با خطا مواجه شد.")
#             return redirect(reverse('account:reset_verify') + f"?token={token}")
#
#         form = CheckOtpForm(request.POST)
#         if not form.is_valid():
#             messages.error(request, "اطلاعات نامعتبر است.")
#             return redirect(reverse('account:reset_verify') + f"?token={token}")
#
#         try:
#             phone = otp_service.verify(token, form.cleaned_data['code'])
#         except OtpExpired:
#             messages.error(request, "کد منقضی شده است. ارسال مجدد را بزنید.")
#             return redirect(reverse('account:reset_verify') + f"?token={token}")
#         except OtpInvalid:
#             messages.error(request, "کد وارد شده صحیح نیست.")
#             return redirect(reverse('account:reset_verify') + f"?token={token}")
#         except OtpError:
#             messages.error(request, "بررسی کد با خطا مواجه شد.")
#             return redirect(reverse('account:reset_verify') + f"?token={token}")
#
#         request.session['reset_phone'] = phone
#         request.session['reset_verified'] = True
#         return redirect('account:set_password')
#
#
# class SetPasswordView(View):
#     template_name = 'account/set_password.html'
#
#     def get(self, request):
#         if not request.session.get('reset_verified'):
#             messages.error(request, "ابتدا کد تایید را وارد کنید.")
#             return redirect('account:forgot_password')
#
#         phone = request.session.get('reset_phone')
#         if not phone:
#             messages.error(request, "شماره قابل شناسایی نیست.")
#             return redirect('account:forgot_password')
#
#         return render(request, self.template_name, {"form": SetPasswordForm(), "phone": phone})
#
#     def post(self, request):
#         if not request.session.get('reset_verified'):
#             messages.error(request, "ابتدا کد تایید را وارد کنید.")
#             return redirect('account:forgot_password')
#
#         phone = request.session.get('reset_phone')
#         if not phone:
#             messages.error(request, "شماره قابل شناسایی نیست.")
#             return redirect('account:forgot_password')
#
#         form = SetPasswordForm(request.POST)
#         if not form.is_valid():
#             return render(request, self.template_name, {"form": form, "phone": phone})
#
#         try:
#             user = User.objects.get(phone=phone)
#         except User.DoesNotExist:
#             messages.error(request, "کاربری با این شماره وجود ندارد.")
#             return redirect('account:forgot_password')
#
#         user.set_password(form.cleaned_data['new_password1'])
#         user.save()
#
#         # خروج از همهٔ سشن‌ها (همه دستگاه‌ها)
#         for s in Session.objects.all():
#             data = s.get_decoded()
#             if data.get('_auth_user_id') == str(user.id):
#                 s.delete()
#
#         request.session.pop('reset_verified', None)
#         request.session.pop('reset_phone', None)
#
#         messages.success(request, "رمز عبور با موفقیت تنظیم شد. اکنون وارد شوید.")
#         return redirect('account:otp_login')
#
#
# @method_decorator(ratelimit(key='ip', rate=RATE_IP, method='POST', block=True), name='dispatch')
# @method_decorator(ratelimit(key='post:phone', rate=RATE_PHONE, method='POST', block=False), name='dispatch')
# class PasswordLoginView(View):
#     template_name = 'account/login.html'
#
#     def _resolve_phone(self, request):
#         # 1) از سشن
#         phone = request.session.get("otp_phone")
#         if phone:
#             return phone
#
#         # 2) از روی توکن
#         token = request.GET.get("token")
#         if token:
#             sess = OtpSession.objects.filter(token=token).order_by('-created_at').first()
#             if sess:
#                 request.session["otp_phone"] = sess.phone
#                 return sess.phone
#         return None
#
#     def get(self, request):
#         phone = self._resolve_phone(request)
#         if not phone:
#             messages.error(request, "شماره موبایل یافت نشد. لطفاً دوباره شماره را وارد کنید.")
#             return redirect('account:otp_login')
#
#         return render(request, self.template_name, {
#             "form": PasswordOnlyForm(),
#             "phone": phone
#         })
#
#     def post(self, request):
#         phone = request.session.get("otp_phone")
#         if not phone:
#             messages.error(request, "جلسه منقضی شده است. دوباره شماره را وارد کنید.")
#             return redirect('account:otp_login')
#
#         form = PasswordOnlyForm(request.POST)
#         if not form.is_valid():
#             return render(request, self.template_name, {"form": form, "phone": phone})
#
#         user = authenticate(request, username=phone, password=form.cleaned_data["password"])
#         if user is None:
#             messages.error(request, "رمز عبور نادرست است.")
#             return render(request, self.template_name, {"form": form, "phone": phone})
#
#         login(request, user)
#         request.session.pop("otp_phone", None)  # پاکسازی بعد از ورود موفق
#         return redirect('home:home')
#
#
#
# class OtpLoginView(View):
#     template_name = 'account/otp_login.html'
#
#     def get(self, request):
#         return render(request, self.template_name, {'form': RegisterForm()})
#
#     def post(self, request):
#         form = RegisterForm(request.POST)
#         if not form.is_valid():
#             return render(request, self.template_name, {'form': form})
#         phone = form.cleaned_data['phone']
#         try:
#             token = otp_service.create_session(phone)
#             request.session["otp_phone"] = phone  # ← شماره برای صفحه‌ی login با رمز
#             # return redirect(reverse('account:check_otp') + f"?token={token}")
#         except OtpBlocked:
#             messages.error(request, "به دلیل تعدد تلاش‌ها تا یک ساعت امکان ارسال کد ندارید.")
#             return redirect('account:otp_login')
#         except OtpTooSoon:
#             messages.error(request, "لطفاً ۶۰ ثانیه بعد دوباره تلاش کنید.")
#             return redirect('account:otp_login')
#         except OtpError:
#             messages.error(request, "خطا در ارسال کد. دوباره تلاش کنید.")
#             return redirect('account:otp_login')
#
#         return redirect(reverse('account:check_otp') + f"?token={token}")
#
#
# class CheckOtpView(View):
#     template_name = 'account/otp_check.html'
#
#     def get(self, request):
#         token = request.GET.get('token')
#         phone = None
#         if token:
#             sess = OtpSession.objects.filter(token=token, is_used=False).first()
#             phone = getattr(sess, 'phone', None)
#         return render(request, self.template_name, {
#             'form': CheckOtpForm(),
#             'token': token,
#             'phone': phone,
#             'seconds_left': otp_service.seconds_left(token) if token else 0,
#             'resend_left': otp_service.resends_left(token) if token else 0,
#         })
#
#     def post(self, request):
#         token = request.GET.get('token')
#         if not token:
#             messages.error(request, "درخواست نامعتبر است.")
#             return redirect('account:otp_login')
#
#         # ارسال مجدد
#         if request.POST.get('resend') == '1':
#             try:
#                 otp_service.resend(token)
#                 messages.success(request, "کد جدید ارسال شد.")
#             except OtpBlocked:
#                 messages.error(request, "تا یک ساعت امکان ارسال کد ندارید.")
#                 return redirect('account:otp_login')
#             except OtpMaxReached:
#                 messages.error(request, "حداکثر ۳ بار ارسال مجدد انجام شد. تا یک ساعت مسدود شدید.")
#                 return redirect('account:otp_login')
#             except OtpTooSoon:
#                 messages.error(request, "لطفاً کمی صبر کنید و دوباره تلاش کنید.")
#             except OtpError:
#                 messages.error(request, "ارسال مجدد با خطا مواجه شد.")
#             return redirect(reverse('account:check_otp') + f"?token={token}")
#
#         # اعتبارسنجی کد
#         form = CheckOtpForm(request.POST)
#         if not form.is_valid():
#             messages.error(request, "اطلاعات نامعتبر است.")
#             return redirect(reverse('account:check_otp') + f"?token={token}")
#
#         try:
#             phone = otp_service.verify(token, form.cleaned_data['code'])
#         except OtpExpired:
#             messages.error(request, "کد منقضی شده است. ارسال مجدد را بزنید.")
#             return redirect(reverse('account:check_otp') + f"?token={token}")
#         except OtpInvalid:
#             messages.error(request, "کد وارد شده صحیح نیست.")
#             return redirect(reverse('account:check_otp') + f"?token={token}")
#         except OtpError:
#             messages.error(request, "بررسی کد با خطا مواجه شد.")
#             return redirect(reverse('account:check_otp') + f"?token={token}")
#
#         user, _ = User.objects.get_or_create(phone=phone)
#         login(request, user)
#         return redirect('home:home')
#
# def key_phone_from_session(group, request):
#     # اول شماره‌ی سشن، اگر نبود IP
#     return request.session.get('otp_phone') or request.META.get('REMOTE_ADDR', 'unknown')
#
#
#
# #
# # class UserLogin(View):
# #     template_name = 'account/login.html'
# #
# #     def get(self, request):
# #         return render(request, self.template_name, {'form': LoginForm()})
# #
# #     def post(self, request):
# #         form = LoginForm(request.POST)
# #         if not form.is_valid():
# #             form.add_error(None, 'داده‌های وارد‌شده نامعتبر است')
# #             return render(request, self.template_name, {'form': form})
# #
# #         phone = form.cleaned_data['phone']
# #         password = form.cleaned_data['password']
# #         user = authenticate(request, username=phone, password=password)
# #         if user is not None:
# #             login(request, user)
# #             return redirect('/')
# #         form.add_error(None, 'شماره تلفن یا رمز عبور نامعتبر است')
# #         return render(request, self.template_name, {'form': form})
#
#
# class LogoutView(View):
#     def get(self, request):
#         logout(request)
#         return redirect('home:home')



# account/views.py

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.shortcuts import render, redirect, reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from django_ratelimit.decorators import ratelimit

from .forms import (
    RegisterForm, CheckOtpForm, PasswordOnlyForm,
    ForgotPasswordForm, SetPasswordForm
)

# سرویس‌های اپ OTP
from OTP_app import services as otp_service
from OTP_app.services import OtpBlocked, OtpTooSoon, OtpMaxReached, OtpInvalid, OtpExpired, OtpError
from OTP_app.models import OtpSession  # فقط برای UI

User = get_user_model()

# نرخ‌ها بر اساس محیط
if settings.DEBUG:
    RATE_IP = "100/m"      # dev
    RATE_PHONE = "100/m"
else:
    RATE_IP = "100/m"       # production
    RATE_PHONE = "100/m"

# --- ریت‌لیمیت سبکِ بدون پکیج (برای چند نقطه) ---
def rate_limited(key: str, limit: int, window_seconds: int) -> bool:
    now = timezone.now().timestamp()
    data = cache.get(key)
    if not data:
        cache.set(key, {"count": 1, "start": now}, timeout=window_seconds)
        return False
    count, start = data["count"], data["start"]
    if now - start > window_seconds:
        cache.set(key, {"count": 1, "start": now}, timeout=window_seconds)
        return False
    if count + 1 > limit:
        cache.set(key, {"count": count + 1, "start": start}, timeout=int(window_seconds - (now - start)))
        return True
    cache.set(key, {"count": count + 1, "start": start}, timeout=int(window_seconds - (now - start)))
    return False

# کلید سفارشی برای django-ratelimit: اول phone از سشن، اگر نبود IP
def key_phone_from_session(group, request):
    return request.session.get('otp_phone') or request.META.get('REMOTE_ADDR', 'unknown')


class ForgotPasswordView(View):
    template_name = 'account/forgot_password.html'

    def get(self, request):
        return render(request, self.template_name, {"form": ForgotPasswordForm()})

    def post(self, request):
        ip = request.META.get("REMOTE_ADDR", "unknown")
        # حداکثر 5 درخواست در 3 دقیقه از هر IP
        if rate_limited(f"rl:forgot:ip:{ip}", limit=50, window_seconds=180):
            messages.error(request, "تلاش‌های زیاد. کمی بعد دوباره تلاش کنید.")
            return render(request, self.template_name, {"form": ForgotPasswordForm()})

        form = ForgotPasswordForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        phone = form.cleaned_data["phone"].strip()

        # اگر ضد-enumeration نمی‌خواهی:
        if not User.objects.filter(phone=phone).exists():
            messages.error(request, "کاربری با این شماره یافت نشد.")
            return render(request, self.template_name, {"form": form})

        try:
            token = otp_service.create_session(phone)
        except OtpBlocked:
            messages.error(request, "به دلیل تعدد تلاش‌ها تا یک ساعت امکان ارسال کد ندارید.")
            return render(request, self.template_name, {"form": form})
        except OtpTooSoon:
            messages.error(request, "لطفاً کمی بعد دوباره تلاش کنید.")
            return render(request, self.template_name, {"form": form})
        except OtpError:
            messages.error(request, "ارسال کد با مشکل مواجه شد.")
            return render(request, self.template_name, {"form": form})

        request.session['reset_phone'] = phone
        return redirect(reverse('account:reset_verify') + f"?token={token}")


class ResetVerifyOtpView(View):
    template_name = 'account/reset_verify_otp.html'

    def get(self, request):
        token = request.GET.get('token')
        phone = None
        if token:
            sess = OtpSession.objects.filter(token=token, is_used=False).first()
            phone = getattr(sess, 'phone', None)
        return render(request, self.template_name, {
            'form': CheckOtpForm(),
            'token': token,
            'phone': phone,
            'seconds_left': otp_service.seconds_left(token) if token else 0,
            'resend_left': otp_service.resends_left(token) if token else 0,
        })

    def post(self, request):
        token = request.GET.get('token')
        if not token:
            messages.error(request, "درخواست نامعتبر است.")
            return redirect('account:forgot_password')

        # حداکثر 6 تلاش در 5 دقیقه per-IP
        ip = request.META.get("REMOTE_ADDR", "unknown")
        if rate_limited(f"rl:resetverify:ip:{ip}", limit=50, window_seconds=300):
            messages.error(request, "تلاش‌های زیاد. کمی بعد دوباره امتحان کنید.")
            return redirect(reverse('account:reset_verify') + f"?token={token}")

        # ارسال مجدد
        if request.POST.get('resend') == '1':
            try:
                otp_service.resend(token)
                messages.success(request, "کد جدید ارسال شد.")
            except OtpBlocked:
                messages.error(request, "تا یک ساعت امکان ارسال کد ندارید.")
                return redirect('account:forgot_password')
            except OtpMaxReached:
                messages.error(request, "حداکثر ۳ بار ارسال مجدد انجام شد. تا یک ساعت مسدود شدید.")
                return redirect('account:forgot_password')
            except OtpTooSoon:
                messages.error(request, "کمی صبر کنید و دوباره تلاش کنید.")
            except OtpError:
                messages.error(request, "ارسال مجدد با خطا مواجه شد.")
            return redirect(reverse('account:reset_verify') + f"?token={token}")

        form = CheckOtpForm(request.POST)
        if not form.is_valid():
            messages.error(request, "اطلاعات نامعتبر است.")
            return redirect(reverse('account:reset_verify') + f"?token={token}")

        try:
            phone = otp_service.verify(token, form.cleaned_data['code'])
        except OtpExpired:
            messages.error(request, "کد منقضی شده است. ارسال مجدد را بزنید.")
            return redirect(reverse('account:reset_verify') + f"?token={token}")
        except OtpInvalid:
            messages.error(request, "کد وارد شده صحیح نیست.")
            return redirect(reverse('account:reset_verify') + f"?token={token}")
        except OtpError:
            messages.error(request, "بررسی کد با خطا مواجه شد.")
            return redirect(reverse('account:reset_verify') + f"?token={token}")

        request.session['reset_phone'] = phone
        request.session['reset_verified'] = True
        return redirect('account:set_password')


class SetPasswordView(View):
    template_name = 'account/set_password.html'

    def get(self, request):
        if not request.session.get('reset_verified'):
            messages.error(request, "ابتدا کد تایید را وارد کنید.")
            return redirect('account:forgot_password')

        phone = request.session.get('reset_phone')
        if not phone:
            messages.error(request, "شماره قابل شناسایی نیست.")
            return redirect('account:forgot_password')

        # برای help_text بهتر می‌توان user=None هم داد؛ مهم‌تر در POST است.
        return render(request, self.template_name, {
            "form": SetPasswordForm(),
            "phone": phone
        })

    def post(self, request):
        if not request.session.get('reset_verified'):
            messages.error(request, "ابتدا کد تایید را وارد کنید.")
            return redirect('account:forgot_password')

        phone = request.session.get('reset_phone')
        if not phone:
            messages.error(request, "شماره قابل شناسایی نیست.")
            return redirect('account:forgot_password')

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            messages.error(request, "کاربری با این شماره وجود ندارد.")
            return redirect('account:forgot_password')

        # فرم را با user بساز تا password_validation بر اساس کاربر باشد
        form = SetPasswordForm(user=user, data=request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "phone": phone})

        new_pw = form.cleaned_data['new_password1']
        user.set_password(new_pw)
        user.save()

        # مطمئن شو سشن فعلی یک کلید دارد
        if not request.session.session_key:
            request.session.save()
        current_key = request.session.session_key

        # کاربر را با رمز جدید لاگین کن
        auth_user = authenticate(request, username=phone, password=new_pw)
        if auth_user is None:
            # اگر به هر دلیل نشد، پیام بده و برگرد به فرم
            messages.error(request, "ورود خودکار پس از تغییر رمز ناموفق بود. لطفاً دستی وارد شوید.")
            # پاکسازی فلگ‌ها را همچنان انجام بده
            request.session.pop('reset_verified', None)
            request.session.pop('reset_phone', None)
            return redirect('account:password_login')

        login(request, auth_user)

        # تمام سشن‌های دیگر کاربر را باطل کن (به‌جز همین سشن فعلی)
        for s in Session.objects.all():
            data = s.get_decoded()
            if data.get('_auth_user_id') == str(user.id) and s.session_key != current_key:
                s.delete()

        # پاکسازی فلگ‌های بازیابی
        request.session.pop('reset_verified', None)
        request.session.pop('reset_phone', None)

        messages.success(request, "رمز عبور با موفقیت تنظیم شد و وارد شدید.")
        return redirect('home:home')

@method_decorator(ratelimit(key='ip', rate=RATE_IP, method='POST', block=True), name='dispatch')
@method_decorator(ratelimit(key=key_phone_from_session, rate=RATE_PHONE, method='POST', block=False), name='dispatch')
class PasswordLoginView(View):
    template_name = 'account/login.html'

    def _resolve_phone(self, request):
        # 1) از سشن
        phone = request.session.get("otp_phone")
        if phone:
            return phone
        # 2) از روی توکن
        token = request.GET.get("token")
        if token:
            sess = OtpSession.objects.filter(token=token).order_by('-created_at').first()
            if sess:
                request.session["otp_phone"] = sess.phone
                return sess.phone
        return None

    def get(self, request):
        phone = self._resolve_phone(request)
        if not phone:
            messages.error(request, "شماره موبایل یافت نشد. لطفاً دوباره شماره را وارد کنید.")
            return redirect('account:otp_login')

        return render(request, self.template_name, {"form": PasswordOnlyForm(), "phone": phone})

    def post(self, request):
        # اگر decorator دوم با block=False لیمیت زده باشد:
        if getattr(request, 'limited', False):
            messages.error(request, "تلاش‌های زیاد. کمی بعد دوباره تلاش کنید.")
            phone = request.session.get("otp_phone")
            return render(request, self.template_name, {"form": PasswordOnlyForm(), "phone": phone})

        phone = request.session.get("otp_phone")
        if not phone:
            messages.error(request, "جلسه منقضی شده است. دوباره شماره را وارد کنید.")
            return redirect('account:otp_login')

        form = PasswordOnlyForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "phone": phone})

        user = authenticate(request, username=phone, password=form.cleaned_data["password"])
        if user is None:
            messages.error(request, "رمز عبور نادرست است.")
            return render(request, self.template_name, {"form": form, "phone": phone})

        login(request, user)
        request.session.pop("otp_phone", None)
        return redirect('home:home')


class OtpLoginView(View):
    template_name = 'account/otp_login.html'

    def get(self, request):
        return render(request, self.template_name, {'form': RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})
        phone = form.cleaned_data['phone']
        try:
            token = otp_service.create_session(phone)
            request.session["otp_phone"] = phone  # برای صفحه‌ی login با رمز
        except OtpBlocked:
            messages.error(request, "به دلیل تعدد تلاش‌ها تا یک ساعت امکان ارسال کد ندارید.")
            return redirect('account:otp_login')
        except OtpTooSoon:
            messages.error(request, "لطفاً ۶۰ ثانیه بعد دوباره تلاش کنید.")
            return redirect('account:otp_login')
        except OtpError:
            messages.error(request, "خطا در ارسال کد. دوباره تلاش کنید.")
            return redirect('account:otp_login')

        return redirect(reverse('account:check_otp') + f"?token={token}")


class CheckOtpView(View):
    template_name = 'account/otp_check.html'

    def get(self, request):
        token = request.GET.get('token')
        phone = None
        if token:
            sess = OtpSession.objects.filter(token=token, is_used=False).first()
            phone = getattr(sess, 'phone', None)
        return render(request, self.template_name, {
            'form': CheckOtpForm(),
            'token': token,
            'phone': phone,
            'seconds_left': otp_service.seconds_left(token) if token else 0,
            'resend_left': otp_service.resends_left(token) if token else 0,
        })

    def post(self, request):
        token = request.GET.get('token')
        if not token:
            messages.error(request, "درخواست نامعتبر است.")
            return redirect('account:otp_login')

        # ارسال مجدد
        if request.POST.get('resend') == '1':
            try:
                otp_service.resend(token)
                messages.success(request, "کد جدید ارسال شد.")
            except OtpBlocked:
                messages.error(request, "تا یک ساعت امکان ارسال کد ندارید.")
                return redirect('account:otp_login')
            except OtpMaxReached:
                messages.error(request, "حداکثر ۳ بار ارسال مجدد انجام شد. تا یک ساعت مسدود شدید.")
                return redirect('account:otp_login')
            except OtpTooSoon:
                messages.error(request, "لطفاً کمی صبر کنید و دوباره تلاش کنید.")
            except OtpError:
                messages.error(request, "ارسال مجدد با خطا مواجه شد.")
            return redirect(reverse('account:check_otp') + f"?token={token}")

        # اعتبارسنجی
        form = CheckOtpForm(request.POST)
        if not form.is_valid():
            messages.error(request, "اطلاعات نامعتبر است.")
            return redirect(reverse('account:check_otp') + f"?token={token}")

        try:
            phone = otp_service.verify(token, form.cleaned_data['code'])
        except OtpExpired:
            messages.error(request, "کد منقضی شده است. ارسال مجدد را بزنید.")
            return redirect(reverse('account:check_otp') + f"?token={token}")
        except OtpInvalid:
            messages.error(request, "کد وارد شده صحیح نیست.")
            return redirect(reverse('account:check_otp') + f"?token={token}")
        except OtpError:
            messages.error(request, "بررسی کد با خطا مواجه شد.")
            return redirect(reverse('account:check_otp') + f"?token={token}")

        user, _ = User.objects.get_or_create(phone=phone)
        login(request, user)
        return redirect('home:home')


# اگر لیمیت غیرفعال است، دکوریتورِ no-op بساز
if not getattr(settings, "ENABLE_RATE_LIMIT", True):
    def ratelimit(*args, **kwargs):
        # decorator that does nothing
        def _deco(fn):
            return fn
        return _deco

# همچنین اگر فانکشن cache-based هم داری، همون‌جا صفرش کن:
def rate_limited(key: str, limit: int, window_seconds: int) -> bool | None:
    if not getattr(settings, "ENABLE_RATE_LIMIT", True):
        return False  # هیچ‌وقت لیمیت نزن
    return None
    # ... بقیه‌ی کد اصلی‌ات ...

class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('home:home')
