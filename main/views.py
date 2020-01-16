import datetime
import time

from django.shortcuts import HttpResponseRedirect, reverse, render, redirect
from django.views.generic.edit import FormView
from django.views.generic.list import ListView
from django.shortcuts import get_object_or_404
from main import forms, models
from django import forms as django_forms

from django.views.generic.base import View
from django.urls import reverse_lazy
from django.http import JsonResponse
from .processing import NewProcess


import logging
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

logger = logging.getLogger(__name__)


def create_project(request):
    if request.method == 'POST':
        form = forms.CreateProjectForm(request.POST)
        if form.is_valid():
            try:
                if models.Project.objects.filter(owner=request.user, name=form.cleaned_data['create_project_name']):
                    messages.error(request, 'Project with the same name already exists')
                else:
                    models.Project.objects.create(
                        owner=request.user,
                        name=form.cleaned_data['create_project_name'],
                        description=form.cleaned_data['create_project_description']
                    )
                    messages.success(request, 'Project created!')
            except:
                messages.error(request, 'Internal problem creating a new project, please contact admin.')
        else:
            messages.error(request, 'form invalid')
        return redirect('/')
    return redirect('/')


class Home(View):
    def get(self, request):
        context = {}
        if request.user.is_authenticated:
            context = {'projects': models.Project.objects.filter(owner=request.user)}
        return render(request, "home.html", context=context)


class FileUploadView(View):
    success_url = reverse_lazy('home')
    template_name = 'home.html'

    def post(self, request, *args, **kwargs):
        print('post', request.POST.keys())
        print(request.POST.getlist('noDebarcoding_sampleName'))
        uploaded = request.FILES.getlist('fileupload')
        try:
            print(request.POST['new_dataset_focus'])
        except:
            print('>NO type here')

        process = NewProcess(request.POST, request.user, uploaded)
        process.new_dataset()
        print('files processed')


        for i in range(len(uploaded)):
            file = uploaded[i]
            filename = str(file)
            print('>filename\t', filename)

        messages.info(request, 'upload successfull')
        return redirect('/')


class EmailConfirmationView(LoginRequiredMixin, FormView):
    template_name = 'home.html'
    form_class = forms.EmailConfirmationForm
    success_url = '/'

    def form_valid(self, form):
        sent_key = form.cleaned_data.get('email_code')
        confirmation = models.EmailConfirmation.objects.get(user=self.request.user)
        if confirmation.sent_key == sent_key:
            form.update_model(confirmation)
            messages.success(self.request, 'Your e-mail is confirmed. Why don\'t you start with the tutorials?')
        else:
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