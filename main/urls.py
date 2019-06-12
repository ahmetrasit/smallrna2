from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from main import views, forms


urlpatterns = [
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('ask/', TemplateView.as_view(template_name='home.html'), name='ask'),
    path('tell/', views.tell, name='tell'),
    path('contact/', views.ContactUsView.as_view(), name='contact'),
    path('questions/<slug:tag>/', views.QuestionListView.as_view(), name='questions'),
    path('sign-up/', views.SignUpView.as_view(), name='signup'),
    path('sign-in/', auth_views.LoginView.as_view(template_name='sign-in.html', form_class=forms.AuthenticationForm), name='sign-in'),
    path('sign-out/', views.sign_out, name='sign-out'),
    path('confirm_email/', views.EmailConfirmationView.as_view(), name='confirm_email'),
]
