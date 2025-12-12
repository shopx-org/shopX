from django.shortcuts import render
from django.views.generic import TemplateView
from .models import TermsAndConditions


class Home(TemplateView):
    template_name = 'home/index.html'



class Terms(TemplateView):
    template_name = "home/terms.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["terms"] = TermsAndConditions.objects.first()
        return context