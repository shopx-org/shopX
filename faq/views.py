from django.shortcuts import render
from .models import FAQCategory


def faq_view(request):
    categories = FAQCategory.objects.prefetch_related('faqs').all()
    return render(request, "faq/faq.html", {"categories": categories})
