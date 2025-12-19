from django.shortcuts import render
from django.views.generic import TemplateView
from .models import TermsAndConditions, HomeVideoBanner


class Home(TemplateView):
    template_name = 'home/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['video_banner'] = (
            HomeVideoBanner.objects
            .filter(is_active=True)
            .only(
                'title_small',
                'title_big',
                'banner_image',
                'video_file'
            )
            .first()
        )
        return context


class Terms(TemplateView):
    template_name = "home/terms.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["terms"] = TermsAndConditions.objects.first()
        return context
    

def page404(request, exception=None):
    return render(request, 'home/404.html', status=404)