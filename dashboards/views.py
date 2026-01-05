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
from django.db import IntegrityError



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
            try:
                form.save()
            except IntegrityError:
                # خطای یونیک بودن کد ملی (یا سایر فیلدهای یونیک) -> به فرم اضافه کن تا هم پیام بگیری هم زیر فیلد بشه نشون داد
                form.add_error("national_id", "این کد ملی قبلاً برای حساب کاربری دیگری ثبت شده است.")
                # اگر فقط می‌خوای messages داشته باشی:
                messages.error(request, "این کد ملی قبلاً برای حساب کاربری دیگری ثبت شده است.")
                return render(request, self.template_name, {'form': form})

            messages.success(request, 'اطلاعات با موفقیت ذخیره شد.')

            if form.cleaned_data.get('new_password'):
                messages.success(request, 'رمز عبور تغییر کرد. لطفاً دوباره وارد شوید.')
                return redirect('account:logout')

            return redirect('dashboards:personal_info')

        # فرم نامعتبر
        for field, errors in form.errors.items():
            for error in errors:
                # field ممکنه "__all__" باشه (non-field errors) و اون موقع form.fields[field] نداریم
                if field in form.fields:
                    messages.error(request, f"{form.fields[field].label}: {error}")
                else:
                    messages.error(request, str(error))

        return render(request, self.template_name, {'form': form})

    # def post(self, request):
    #     form = DashboardAccountForm(request.POST, instance=request.user, user=request.user)
    #     if form.is_valid():
    #         form.save()
    #         messages.success(request, 'اطلاعات با موفقیت ذخیره شد.')
    #         if form.cleaned_data.get('new_password'):
    #             messages.success(request, 'رمز عبور تغییر کرد. لطفاً دوباره وارد شوید.')
    #             return redirect('account:logout')
    #         return redirect('dashboards:personal_info')
    #     else:
    #         for field, errors in form.errors.items():
    #             for error in errors:
    #                 messages.error(request, f"{form.fields[field].label}: {error}")
    #     return render(request, self.template_name, {'form': form})


@method_decorator(login_required, name='dispatch')
class ChangePhoneOtpView(View):
    template_name = "dashboards/change_phone_number.html"

    # ===============================
    # GET → نمایش صفحه
    # ===============================
    def get(self, request):
        form = ChangePhoneNumberForm(user=request.user)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "phone": request.user.phone
            }
        )

    # ===============================
    # POST → منطق OTP
    # ===============================
    def post(self, request):
        stage = request.POST.get("stage")
        code  = request.POST.get("code")
        new_phone = request.POST.get("new_phone", "").strip()
        sess = request.session

        try:
            # STEP 1: send OTP to old phone
            if stage == "send_old":
                form = ChangePhoneNumberForm(
                    {"new_phone": new_phone},
                    user=request.user
                )
                if not form.is_valid():
                    msg = next(iter(form.errors.values()))[0]
                    return JsonResponse({"status": "error", "message": msg})

                token = otp_services.create_session(request.user.phone)

                sess["otp_old_token"] = token
                sess["pending_new_phone"] = form.cleaned_data["new_phone"]
                sess.modified = True

                return JsonResponse({
                    "status": "ok",
                    "stage": "verify_old",
                    "message": "کد تأیید به شماره فعلی ارسال شد."
                })

            # STEP 2: verify old phone
            elif stage == "verify_old":
                token = sess.get("otp_old_token")
                if not token:
                    return JsonResponse({"status": "error", "message": "توکن یافت نشد."})

                otp_services.verify(token, code)

                new_phone = sess.get("pending_new_phone")
                if User.objects.filter(phone=new_phone).exists():
                    return JsonResponse({
                        "status": "error",
                        "message": "شماره جدید قبلاً ثبت شده است."
                    })

                token_new = otp_services.create_session(new_phone)
                sess["otp_new_token"] = token_new
                sess.modified = True

                return JsonResponse({
                    "status": "ok",
                    "stage": "verify_new",
                    "message": "کد تأیید به شماره جدید ارسال شد."
                })

            # STEP 3: verify new phone
            elif stage == "verify_new":
                token = sess.get("otp_new_token")
                new_phone = sess.get("pending_new_phone")

                if not token or not new_phone:
                    return JsonResponse({
                        "status": "error",
                        "message": "اطلاعات ناقص است."
                    })

                otp_services.verify(token, code)

                request.user.phone = new_phone
                request.user.save(update_fields=["phone"])

                sess.flush()

                return JsonResponse({
                    "status": "done",
                    "message": "شماره موبایل با موفقیت تغییر یافت."
                })

            return JsonResponse({
                "status": "error",
                "message": "مرحله نامعتبر است."
            })

        # ===== OTP errors =====
        except otp_services.OtpBlocked:
            return JsonResponse({
                "status": "error",
                "message": "ارسال کد برای این شماره موقتاً مسدود شده است."
            })
        except otp_services.OtpTooSoon:
            return JsonResponse({
                "status": "error",
                "message": "لطفاً کمی صبر کنید."
            })
        except otp_services.OtpExpired:
            return JsonResponse({
                "status": "error",
                "message": "کد منقضی شده است."
            })
        except otp_services.OtpInvalid:
            return JsonResponse({
                "status": "error",
                "message": "کد وارد شده اشتباه است."
            })
        except Exception:
            return JsonResponse({
                "status": "error",
                "message": "خطای داخلی سرور"
            })


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