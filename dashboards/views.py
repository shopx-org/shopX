from django.shortcuts import render

# Create your views here.
def user_dashboard(request):
    return render(request, 'dashboards/user_dash_index.html')



def user_profile(request):
    return render(request, 'dashboards/user_profile.html')
