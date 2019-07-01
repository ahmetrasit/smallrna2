from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models



class UserManager(BaseUserManager):
    use_in_migrations = True
    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('You need to provide a valid e-mail address')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self.db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField('email address', unique=True)
    first_name = models.CharField(max_length=64, null=True)
    last_name = models.CharField(max_length=64, null=True)
    email_confirmed = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = UserManager()


class EmailConfirmation(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    sent_key = models.CharField(max_length=16)
    status = models.BooleanField(default=False)  #True if confirmed, False if waiting
    created_on = models.DateTimeField(auto_now=True)
    confirmed_on = models.DateTimeField(null=True)


class ProcessedData(models.Model):
    owner = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    description = models.TextField()
    data_type = models.TextField()
    path = models.TextField()
    status = models.CharField(max_length=32)
    info = models.TextField()
    created_on = models.DateTimeField(auto_now=True)
    finished_on = models.DateTimeField(null=True)


class Sample(models.Model):
    name = models.CharField(max_length=128)
    description = models.TextField()
    processed_data = models.ForeignKey(ProcessedData, on_delete=models.DO_NOTHING)
    created_on = models.DateTimeField(auto_now=True)


class Dataset(models.Model):
    owner = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    samples = models.ForeignKey(Sample, on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=128)
    description = models.TextField()
    public = models.BooleanField(default=False)
    initial_data_path = models.TextField()
    created_on = models.DateTimeField(auto_now=True)


class Project(models.Model):
    name = models.CharField(max_length=128)
    description = models.TextField(null=False)
    owner = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    other_users = models.ForeignKey(User, on_delete=models.DO_NOTHING, null=True, related_name='other_users')
    dataset = models.ForeignKey(Dataset, on_delete=models.DO_NOTHING, null=True)
    public = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now=True)


class GUITemplate(models.Model):
    name = models.CharField(max_length=128)
    description = models.TextField()
    type = models.CharField(max_length=64)
    html_path = models.TextField()
    created_on = models.DateTimeField(auto_now=True)


class Stats(models.Model):
    type = models.CharField(max_length=64)
    count = models.IntegerField(default=0)
    object_list = models.TextField()
    created_on = models.DateTimeField(auto_now=True)


class Task(models.Model):
    name = models.TextField()
    task_type = models.CharField(max_length=64, default='processing')
    status = models.TextField(default='waiting')
    message = models.TextField(null=True)
    created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    created_on = models.DateField(auto_now=True)
    finished_on = models.DateField(null=True)
