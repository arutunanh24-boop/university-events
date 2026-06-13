import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from openpyxl import Workbook

from accounts.decorators import organizer_or_admin_required

from .forms import CommentForm, EventFileForm, EventForm
from .models import Category, Comment, Event, EventFile, Location, Notification, Registration, Tag
from .services import can_manage_event, event_statistics_queryset, notify_registered_participants


def event_list(request):
    events = event_statistics_queryset(
        Event.objects.select_related('category', 'location', 'organizer', 'organization').prefetch_related('tags')
    )
    if not request.user.is_authenticated:
        events = events.filter(status=Event.Status.PUBLISHED)
    elif not request.user.is_coursework_admin:
        events = events.filter(Q(status=Event.Status.PUBLISHED) | Q(organizer=request.user))

    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category')
    tag_id = request.GET.get('tag')
    status = request.GET.get('status')

    if query:
        events = events.filter(Q(title__icontains=query) | Q(description__icontains=query))
    if category_id:
        events = events.filter(category_id=category_id)
    if tag_id:
        events = events.filter(tags__id=tag_id)
    if status and request.user.is_authenticated and request.user.is_coursework_admin:
        events = events.filter(status=status)

    context = {
        'events': events.distinct(),
        'categories': Category.objects.all(),
        'tags': Tag.objects.all(),
        'selected': {'q': query, 'category': category_id, 'tag': tag_id, 'status': status},
        'status_choices': Event.Status.choices,
    }
    return render(request, 'events/event_list.html', context)


def event_detail(request, pk):
    event = get_object_or_404(
        Event.objects.select_related('category', 'location', 'organizer', 'organization').prefetch_related('tags'),
        pk=pk,
    )
    registration = None
    if request.user.is_authenticated:
        registration = Registration.objects.filter(user=request.user, event=event).first()

    context = {
        'event': event,
        'registration': registration,
        'can_manage': can_manage_event(request.user, event),
        'file_form': EventFileForm(),
        'comment_form': CommentForm(),
        'comments': event.comments.select_related('user'),
        'registered_count': event.registered_count,
    }
    return render(request, 'events/event_detail.html', context)


@organizer_or_admin_required
def event_create(request):
    form = EventForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        event = form.save(commit=False)
        event.organizer = request.user
        event.save()
        form.save_m2m()
        messages.success(request, 'Мероприятие создано.')
        return redirect('events:event_detail', pk=event.pk)
    return render(request, 'events/event_form.html', {'form': form, 'title': 'Создание мероприятия'})


@login_required
def event_edit(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not can_manage_event(request.user, event):
        messages.error(request, 'Можно редактировать только свои мероприятия.')
        return redirect('events:event_detail', pk=event.pk)

    old_values = {
        'start_datetime': event.start_datetime,
        'end_datetime': event.end_datetime,
        'status': event.status,
        'title': event.title,
        'location_id': event.location_id,
    }
    form = EventForm(request.POST or None, request.FILES or None, instance=event)
    if request.method == 'POST' and form.is_valid():
        event = form.save(commit=False)
        event.organizer = event.organizer or request.user
        event.save()
        form.save_m2m()
        _notify_about_event_changes(event, old_values)
        messages.success(request, 'Мероприятие обновлено.')
        return redirect('events:event_detail', pk=event.pk)
    return render(request, 'events/event_form.html', {'form': form, 'event': event, 'title': 'Редактирование мероприятия'})


@login_required
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not can_manage_event(request.user, event):
        messages.error(request, 'Удалять можно только свои мероприятия.')
        return redirect('events:event_detail', pk=event.pk)
    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Мероприятие удалено.')
        return redirect('events:event_list')
    return render(request, 'events/event_confirm_delete.html', {'event': event})


@login_required
def register_for_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method != 'POST':
        return redirect('events:event_detail', pk=event.pk)
    if event.status != Event.Status.PUBLISHED:
        messages.error(request, 'Регистрация доступна только на опубликованные мероприятия.')
        return redirect('events:event_detail', pk=event.pk)
    if event.start_datetime <= timezone.now():
        messages.error(request, 'Регистрация на прошедшее мероприятие закрыта.')
        return redirect('events:event_detail', pk=event.pk)
    current_registration = Registration.objects.filter(user=request.user, event=event).first()
    if event.is_full and not (current_registration and current_registration.status == Registration.Status.REGISTERED):
        messages.error(request, 'Лимит участников уже достигнут.')
        return redirect('events:event_detail', pk=event.pk)
    registration, created = Registration.objects.get_or_create(user=request.user, event=event)
    if created:
        messages.success(request, 'Вы зарегистрировались на мероприятие.')
    elif registration.status == Registration.Status.REGISTERED:
        messages.info(request, 'Вы уже зарегистрированы на это мероприятие.')
    else:
        registration.status = Registration.Status.REGISTERED
        registration.registered_at = timezone.now()
        registration.save(update_fields=['status', 'registered_at'])
        messages.success(request, 'Вы зарегистрировались на мероприятие.')
    return redirect('events:event_detail', pk=event.pk)


@login_required
def cancel_registration(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        registration = Registration.objects.filter(user=request.user, event=event).first()
        if registration and registration.status == Registration.Status.REGISTERED:
            registration.status = Registration.Status.CANCELLED
            registration.save(update_fields=['status'])
            messages.success(request, 'Регистрация отменена.')
        else:
            messages.info(request, 'Активной регистрации не найдено.')
    return redirect('events:event_detail', pk=event.pk)


@login_required
def my_registrations(request):
    registrations = (
        Registration.objects.filter(user=request.user)
        .select_related('event', 'event__category', 'event__location')
        .order_by('-registered_at')
    )
    return render(request, 'events/my_registrations.html', {'registrations': registrations})


@login_required
def participant_list(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not can_manage_event(request.user, event):
        messages.error(request, 'Список участников доступен организатору и администратору.')
        return redirect('events:event_detail', pk=event.pk)
    registrations = event.registrations.filter(status=Registration.Status.REGISTERED).select_related('user', 'user__organization')
    return render(request, 'events/participants.html', {'event': event, 'registrations': registrations})


@login_required
def export_participants_csv(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not can_manage_event(request.user, event):
        messages.error(request, 'Выгрузка доступна организатору и администратору.')
        return redirect('events:event_detail', pk=event.pk)

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="participants_event_{event.pk}.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['Фамилия', 'Имя', 'Отчество', 'Email', 'Организация', 'Дата регистрации'])
    for registration in event.registrations.filter(status=Registration.Status.REGISTERED).select_related('user', 'user__organization'):
        user = registration.user
        writer.writerow([
            user.last_name,
            user.first_name,
            user.middle_name,
            user.email,
            user.organization.name if user.organization else '',
            registration.registered_at.strftime('%d.%m.%Y %H:%M'),
        ])
    return response


@login_required
def export_participants_xlsx(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not can_manage_event(request.user, event):
        messages.error(request, 'Выгрузка доступна организатору и администратору.')
        return redirect('events:event_detail', pk=event.pk)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Участники'
    sheet.append(['Фамилия', 'Имя', 'Отчество', 'Email', 'Организация', 'Дата регистрации'])
    for registration in event.registrations.filter(status=Registration.Status.REGISTERED).select_related('user', 'user__organization'):
        user = registration.user
        sheet.append([
            user.last_name,
            user.first_name,
            user.middle_name,
            user.email,
            user.organization.name if user.organization else '',
            registration.registered_at.strftime('%d.%m.%Y %H:%M'),
        ])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="participants_event_{event.pk}.xlsx"'
    workbook.save(response)
    return response


@login_required
def upload_event_file(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not can_manage_event(request.user, event):
        messages.error(request, 'Загружать файлы может только организатор или администратор.')
        return redirect('events:event_detail', pk=event.pk)
    form = EventFileForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        event_file = form.save(commit=False)
        event_file.event = event
        event_file.uploaded_by = request.user
        event_file.save()
        messages.success(request, 'Файл прикреплен к мероприятию.')
    else:
        messages.error(request, 'Не удалось загрузить файл. Проверьте форму.')
    return redirect('events:event_detail', pk=event.pk)


@login_required
def delete_event_file(request, pk):
    event_file = get_object_or_404(EventFile.objects.select_related('event'), pk=pk)
    event = event_file.event
    if not can_manage_event(request.user, event):
        messages.error(request, 'Удалять файлы может только организатор или администратор.')
        return redirect('events:event_detail', pk=event.pk)
    if request.method == 'POST':
        event_file.delete()
        messages.success(request, 'Файл удален.')
    return redirect('events:event_detail', pk=event.pk)


@login_required
def add_comment(request, pk):
    event = get_object_or_404(Event, pk=pk)
    form = CommentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        comment = form.save(commit=False)
        comment.event = event
        comment.user = request.user
        comment.comment_type = Comment.Type.REVIEW if event.end_datetime <= timezone.now() else Comment.Type.COMMENT
        comment.save()
        messages.success(request, 'Сообщение добавлено.')
    return redirect('events:event_detail', pk=event.pk)


@login_required
def notifications(request):
    if request.method == 'POST':
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        messages.success(request, 'Уведомления отмечены как прочитанные.')
        return redirect('events:notifications')
    items = Notification.objects.filter(user=request.user).select_related('event')
    return render(request, 'events/notifications.html', {'notifications': items})


def _notify_about_event_changes(event, old_values):
    if old_values['status'] != event.status and event.status == Event.Status.CANCELLED:
        notify_registered_participants(
            event,
            Notification.Type.CANCELLED,
            'Мероприятие отменено',
            f'Мероприятие «{event.title}» было отменено.',
        )
        return
    if old_values['start_datetime'] != event.start_datetime or old_values['end_datetime'] != event.end_datetime:
        notify_registered_participants(
            event,
            Notification.Type.RESCHEDULED,
            'Изменено время мероприятия',
            f'Для мероприятия «{event.title}» изменены дата или время проведения.',
        )
        return
    if old_values['title'] != event.title or old_values['location_id'] != event.location_id:
        notify_registered_participants(
            event,
            Notification.Type.CHANGED,
            'Изменены параметры мероприятия',
            f'В карточке мероприятия «{event.title}» обновлены важные параметры.',
        )
