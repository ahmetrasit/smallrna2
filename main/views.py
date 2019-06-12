import datetime

from django.shortcuts import HttpResponseRedirect, reverse, render, redirect
from django.views.generic.edit import FormView
from django.views.generic.list import ListView
from django.shortcuts import get_object_or_404
from main import forms, models
from django import forms as django_forms

import logging
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

logger = logging.getLogger(__name__)


class EmailConfirmationView(LoginRequiredMixin, FormView):
    template_name = 'home.html'
    form_class = forms.EmailConfirmationForm
    success_url = '/'

    def form_valid(self, form):
        sent_key = form.cleaned_data.get('email_code')
        confirmation = models.EmailConfirmation.objects.get(user=self.request.user)
        if confirmation.sent_key == sent_key:
            form.update_model(confirmation)
            models.UserEvent(user=self.request.user, event='cEM').save()
            messages.success(self.request, 'Your e-mail is confirmed. Why don\'t you start with the tutorials?')
        else:
            models.UserEvent(user=self.request.user, event='wEC').save()
            messages.error(self.request, 'Invalid activation code, please check the code and try again!')
        return super().form_valid(form)


class SignUpView(FormView):
    template_name = 'sign-up.html'
    form_class = forms.UserCreationForm

    def get_success_url(self):
        redirect_to = self.request.GET.get('next', '/')
        messages.info(self.request, 'Signed up successfully. We\'re glad to see you here!')
        return redirect_to

    def form_valid(self, form):
        response = super().form_valid(form)
        form.save()
        email = form.cleaned_data.get('email')
        raw_pass = form.cleaned_data.get('password1')
        logger.info('new signup for %s through SignUpView', email)
        user = authenticate(email=email, password=raw_pass)
        print(user)
        login(self.request, user)
        code = form.create_email_confirmation_code(user)
        form.send_mail(code)
        messages.info(self.request, 'Signed up successfully. We\'re glad to see you here!')
        return response


@login_required(login_url='/sign-in/')
def sign_out(request):
    logout(request)
    return HttpResponseRedirect(reverse('sign-in'))