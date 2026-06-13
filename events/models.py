from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from accounts.models import Organization


class Category(models.Model):
    name = models.CharField('Название', max_length=120, unique=True)
    description = models.TextField('Описание', blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField('Название', max_length=80, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Location(models.Model):
    name = models.CharField('Название', max_length=150)
    building = models.CharField('Корпус', max_length=80, blank=True)
    room = models.CharField('Аудитория', max_length=80, blank=True)
    address = models.CharField('Адрес', max_length=220, blank=True)
    description = models.TextField('Описание', blank=True)

    class Meta:
        ordering = ['name', 'building', 'room']
        verbose_name = 'Место проведения'
        verbose_name_plural = 'Места проведения'

    def __str__(self):
        details = ', '.join(part for part in [self.building, self.room] if part)
        return f'{self.name} ({details})' if details else self.name


class Event(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        PUBLISHED = 'published', 'Опубликовано'
        CANCELLED = 'cancelled', 'Отменено'
        COMPLETED = 'completed', 'Завершено'

    title = models.CharField('Название', max_length=220)
    description = models.TextField('Описание')
    start_datetime = models.DateTimeField('Дата и время начала')
    end_datetime = models.DateTimeField('Дата и время окончания')
    status = models.CharField('Статус', max_length=20, choices=Status.choices, default=Status.PUBLISHED)
    max_participants = models.PositiveIntegerField('Лимит участников', default=30)
    image = models.ImageField('Изображение', upload_to='event_images/', blank=True)
    category = models.ForeignKey(Category, verbose_name='Категория', on_delete=models.PROTECT, related_name='events')
    location = models.ForeignKey(Location, verbose_name='Место проведения', on_delete=models.PROTECT, related_name='events')
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Организатор',
        on_delete=models.CASCADE,
        related_name='organized_events',
    )
    organization = models.ForeignKey(
        Organization,
        verbose_name='Организация',
        on_delete=models.PROTECT,
        related_name='events',
    )
    tags = models.ManyToManyField(Tag, verbose_name='Теги', blank=True, related_name='events')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        ordering = ['-start_datetime']
        verbose_name = 'Мероприятие'
        verbose_name_plural = 'Мероприятия'

    def __str__(self):
        return self.title

    def clean(self):
        if self.end_datetime and self.start_datetime and self.end_datetime <= self.start_datetime:
            raise ValidationError({'end_datetime': 'Дата окончания должна быть позже даты начала.'})
        if self.max_participants < 1:
            raise ValidationError({'max_participants': 'Лимит участников должен быть больше нуля.'})

    @property
    def registered_count(self):
        return self.registrations.filter(status=Registration.Status.REGISTERED).count()

    @property
    def free_places(self):
        return max(self.max_participants - self.registered_count, 0)

    @property
    def is_full(self):
        return self.registered_count >= self.max_participants

    @property
    def is_registration_available(self):
        return self.status == self.Status.PUBLISHED and not self.is_full and self.start_datetime > timezone.now()


class Registration(models.Model):
    class Status(models.TextChoices):
        REGISTERED = 'registered', 'Зарегистрирован'
        CANCELLED = 'cancelled', 'Отменена'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Пользователь', on_delete=models.CASCADE, related_name='registrations')
    event = models.ForeignKey(Event, verbose_name='Мероприятие', on_delete=models.CASCADE, related_name='registrations')
    registered_at = models.DateTimeField('Дата регистрации', auto_now_add=True)
    status = models.CharField('Статус', max_length=20, choices=Status.choices, default=Status.REGISTERED)

    class Meta:
        ordering = ['-registered_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'event'], name='unique_user_event_registration'),
        ]
        verbose_name = 'Регистрация на мероприятие'
        verbose_name_plural = 'Регистрации на мероприятия'

    def __str__(self):
        return f'{self.user} -> {self.event}'


class EventFile(models.Model):
    class FileType(models.TextChoices):
        POSTER = 'poster', 'Афиша'
        PROGRAM = 'program', 'Программа'
        REGULATION = 'regulation', 'Положение'
        PRESENTATION = 'presentation', 'Презентация'
        PARTICIPANTS = 'participants', 'Список участников'
        OTHER = 'other', 'Другое'

    event = models.ForeignKey(Event, verbose_name='Мероприятие', on_delete=models.CASCADE, related_name='files')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Кем загружен', on_delete=models.SET_NULL, null=True)
    file = models.FileField('Файл', upload_to='event_files/')
    file_name = models.CharField('Имя файла', max_length=255, blank=True)
    file_type = models.CharField('Тип файла', max_length=30, choices=FileType.choices, default=FileType.OTHER)
    uploaded_at = models.DateTimeField('Дата загрузки', auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Файл мероприятия'
        verbose_name_plural = 'Файлы мероприятий'

    def save(self, *args, **kwargs):
        if self.file and not self.file_name:
            self.file_name = self.file.name.split('/')[-1]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.file_name or 'Файл мероприятия'


class Notification(models.Model):
    class Type(models.TextChoices):
        RESCHEDULED = 'rescheduled', 'Перенос мероприятия'
        CANCELLED = 'cancelled', 'Отмена мероприятия'
        CHANGED = 'changed', 'Изменение параметров'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Пользователь', on_delete=models.CASCADE, related_name='notifications')
    event = models.ForeignKey(Event, verbose_name='Мероприятие', on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField('Заголовок', max_length=180)
    message = models.TextField('Сообщение')
    notification_type = models.CharField('Тип уведомления', max_length=30, choices=Type.choices)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    is_read = models.BooleanField('Прочитано', default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'

    def __str__(self):
        return self.title


class Comment(models.Model):
    class Type(models.TextChoices):
        COMMENT = 'comment', 'Комментарий'
        REVIEW = 'review', 'Отзыв'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Пользователь', on_delete=models.CASCADE, related_name='comments')
    event = models.ForeignKey(Event, verbose_name='Мероприятие', on_delete=models.CASCADE, related_name='comments')
    content = models.TextField('Текст')
    comment_type = models.CharField('Тип', max_length=20, choices=Type.choices, default=Type.COMMENT)
    created_at = models.DateTimeField('Дата публикации', auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'

    def __str__(self):
        return f'{self.get_comment_type_display()} от {self.user}'
