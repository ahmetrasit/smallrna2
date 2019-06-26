from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from main import views, forms


urlpatterns = [
    path('', views.Home.as_view(), name='home'),
    path('create_project/', views.create_project, name='create_project'),
    path('sign-up/', views.SignUpView.as_view(), name='signup'),
    path('sign-in/', auth_views.LoginView.as_view(template_name='sign-in.html', form_class=forms.AuthenticationForm), name='sign-in'),
    path('sign-out/', views.sign_out, name='sign-out'),
    path('confirm_email/', views.EmailConfirmationView.as_view(), name='confirm_email'),
    path('upload/', views.FileUploadView.as_view(), name='upload'),
]
