import datetime

from django import forms
from django.core.mail import send_mail
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm
from django.contrib.auth.forms import UsernameField
from django.contrib.auth import authenticate
from . import models
import logging
from random import randint

logger = logging.getLogger(__name__)


class EmailConfirmationForm(forms.Form):
    email_code = forms.CharField(min_length=6, max_length=6)

    def update_model(self, confirmation):
        print('update_model')
        confirmation.confirmed_on = datetime.datetime.now()
        confirmation.user.can_ask = True
        confirmation.user.email_confirmed = True
        confirmation.user.save()
        confirmation.status = True
        confirmation.save()


class AuthenticationForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(strip=False, widget=forms.PasswordInput)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        if email is not None and password:
            self.user = authenticate(self.request, email=email, password=password)
            if self.user is None:
                raise forms.ValidationError('Invalid e-mail or password.')
            logger.info(f'{self.user} is logged in')
        return self.cleaned_data

    def get_user(self):
        return self.user


class UserCreationForm(DjangoUserCreationForm):
    class Meta(DjangoUserCreationForm.Meta):
        model = models.User
        fields = ('email',)
        field_classes = {'email':UsernameField}

    def create_email_confirmation_code(self, user):
        random_code = randint(111111, 999999)
        confirmation = models.EmailConfirmation(user=user, sent_key=random_code)
        confirmation.save()
        return random_code

    def send_mail(self, code):
        logger.info('sending sign-up email for %s', self.cleaned_data['email'])

        message = 'Welcome {}! Please enter the following code to confirm your e-mail address: {} '.format(self.cleaned_data['email'], code)
        send_mail('Welcome to smallRNA!', message, 'welcome@smallrna.com',
                  [self.cleaned_data['email']], fail_silently=True)