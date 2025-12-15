from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from django.http import JsonResponse
from time import time

from .models import Contact
from .forms import ContactForm
from Core.models import SiteInfo


@require_http_methods(["GET", "POST"])
def contact_view(request):
    site_info = SiteInfo.objects.first()
    page = Contact.objects.first()
    
    # اگر درخواست AJAX بود:
    if request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        form = ContactForm(request.POST)

        if form.is_valid():
            last_request = request.session.get("last_contact_submit")

            if last_request and time() - last_request < 10:
                return JsonResponse({
                    "success": False,
                    "errors": {"__all__": ["لطفاً چند ثانیه بعد دوباره تلاش کنید."]}
                })
            
            form.save()
            request.session["last_contact_submit"] = time()
            
            return JsonResponse({
                "success": True,
                "message": "پیام شما با موفقیت ارسال شد."
            })

        # ارسال خطاهای ولیدیشن
        return JsonResponse({
            "success": False,
            "errors": form.errors
        })

    # درخواست GET معمولی
    form = ContactForm()
    return render(request, "contact/contact.html", {
        "form": form,
        "site_info": site_info,
        "page": page,
        "success": False,
    })
