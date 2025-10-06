from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import DashboardAccountForm


@method_decorator(login_required, name='dispatch')
class DashboardView(View):
    def get(self, request):
        return render(request, 'dashboards/dashboard.html', {'message': 'خوش آمدید به داشبورد!'})

@method_decorator(login_required, name='dispatch')
class PersonalInfoView(View):
    template_name = 'dashboards/personal_info.html'

    def get(self, request):
        form = DashboardAccountForm(instance=request.user, user=request.user)
        return render(request, self.template_name, {'form': form})

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