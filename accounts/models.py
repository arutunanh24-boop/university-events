from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class Organization(models.Model):
    FACULTY = 'faculty'
    DEPARTMENT = 'department'
    CLUB = 'club'
    SECTION = 'section'
    UNION = 'union'
    OTHER = 'other'

    TYPE_CHOICES = [
        (FACULTY, 'Факультет'),
        (DEPARTMENT, 'Кафедра'),
        (CLUB, 'Клуб'),
        (SECTION, 'Секция'),
        (UNION, 'Студенческое объединение'),
        (OTHER, 'Другое'),
    ]

    name = models.CharField('Название', max_length=180, unique=True)
    type = models.CharField('Тип', max_length=30, choices=TYPE_CHOICES, default=OTHER)
    description = models.TextField('Описание', blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Организация'
        verbose_name_plural = 'Организации'

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Email обязателен')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('role', User.Role.STUDENT)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь is_superuser=True')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'student', 'Студент'
        ORGANIZER = 'organizer', 'Организатор'
        ADMIN = 'admin', 'Администратор'

    username = None
    email = models.EmailField(_('email address'), unique=True)
    middle_name = models.CharField('Отчество', max_length=150, blank=True)
    role = models.CharField('Роль', max_length=20, choices=Role.choices, default=Role.STUDENT)
    organization = models.ForeignKey(
        Organization,
        verbose_name='Организация',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ['last_name', 'first_name', 'email']
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def save(self, *args, **kwargs):
        if self.role == self.Role.ADMIN:
            self.is_staff = True
        elif not self.is_superuser:
            self.is_staff = False
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        parts = [self.last_name, self.first_name, self.middle_name]
        return ' '.join(part for part in parts if part).strip() or self.email

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT and not self.is_superuser

    @property
    def is_organizer(self):
        return self.role == self.Role.ORGANIZER

    @property
    def is_coursework_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    def __str__(self):
        return self.full_name
