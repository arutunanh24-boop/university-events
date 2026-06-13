from django.contrib import messages
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import admin_required
from accounts.models import Organization, User
from events.models import Category, Event, Location, Registration, Tag

from .forms import CategoryForm, LocationForm, OrganizationForm, TagForm, UserAdminForm, UserCreateForm


REFERENCE_CONFIG = {
    'categories': {
        'model': Category,
        'form': CategoryForm,
        'title': 'Категории мероприятий',
        'create_title': 'Создание категории',
        'edit_title': 'Редактирование категории',
        'columns': ['name', 'description'],
    },
    'tags': {
        'model': Tag,
        'form': TagForm,
        'title': 'Теги',
        'create_title': 'Создание тега',
        'edit_title': 'Редактирование тега',
        'columns': ['name'],
    },
    'organizations': {
        'model': Organization,
        'form': OrganizationForm,
        'title': 'Организации',
        'create_title': 'Создание организации',
        'edit_title': 'Редактирование организации',
        'columns': ['name', 'type', 'description'],
    },
    'locations': {
        'model': Location,
        'form': LocationForm,
        'title': 'Места проведения',
        'create_title': 'Создание места',
        'edit_title': 'Редактирование места',
        'columns': ['name', 'building', 'room', 'address'],
    },
}


@admin_required
def dashboard_home(request):
    events = Event.objects.all()
    registrations = Registration.objects.filter(status=Registration.Status.REGISTERED)
    popular_events = (
        events.annotate(reg_count=Count('registrations', filter=Q(registrations__status=Registration.Status.REGISTERED)))
        .order_by('-reg_count', 'title')[:5]
    )
    category_stats = (
        Category.objects.annotate(event_count=Count('events'), reg_count=Count('events__registrations'))
        .order_by('-event_count', 'name')
    )
    location_stats = (
        Location.objects.annotate(event_count=Count('events'))
        .order_by('-event_count', 'name')[:8]
    )
    return render(
        request,
        'dashboard/home.html',
        {
            'users_count': User.objects.count(),
            'events_count': events.count(),
            'registrations_count': registrations.count(),
            'categories_count': Category.objects.count(),
            'popular_events': popular_events,
            'category_stats': category_stats,
            'location_stats': location_stats,
        },
    )


@admin_required
def user_list(request):
    users = User.objects.select_related('organization').all()
    query = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip()
    if query:
        users = users.filter(Q(email__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query))
    if role:
        users = users.filter(role=role)
    return render(request, 'dashboard/users/list.html', {'users': users, 'roles': User.Role.choices, 'selected': {'q': query, 'role': role}})


@admin_required
def user_detail(request, pk):
    user_obj = get_object_or_404(User.objects.select_related('organization'), pk=pk)
    registrations = user_obj.registrations.select_related('event')[:10]
    organized_events = user_obj.organized_events.all()[:10]
    return render(
        request,
        'dashboard/users/detail.html',
        {'user_obj': user_obj, 'registrations': registrations, 'organized_events': organized_events},
    )


@admin_required
def user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user_obj = form.save()
        messages.success(request, 'Пользователь создан.')
        return redirect('dashboard:user_detail', pk=user_obj.pk)
    return render(request, 'dashboard/users/form.html', {'form': form, 'title': 'Создание пользователя'})


@admin_required
def user_update(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    form = UserAdminForm(request.POST or None, instance=user_obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Пользователь обновлен.')
        return redirect('dashboard:user_detail', pk=user_obj.pk)
    return render(request, 'dashboard/users/form.html', {'form': form, 'title': 'Редактирование пользователя', 'user_obj': user_obj})


@admin_required
def user_deactivate(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        if user_obj == request.user:
            messages.error(request, 'Нельзя деактивировать собственную учетную запись.')
        else:
            user_obj.is_active = False
            user_obj.save(update_fields=['is_active'])
            messages.success(request, 'Пользователь деактивирован.')
    return redirect('dashboard:user_list')


@admin_required
def reference_list(request, kind):
    config = _get_reference_config(kind)
    objects = config['model'].objects.all()
    return render(request, 'dashboard/references/list.html', {'kind': kind, 'config': config, 'objects': objects})


@admin_required
def reference_create(request, kind):
    config = _get_reference_config(kind)
    form = config['form'](request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Запись создана.')
        return redirect('dashboard:reference_list', kind=kind)
    return render(request, 'dashboard/references/form.html', {'form': form, 'title': config['create_title'], 'kind': kind})


@admin_required
def reference_update(request, kind, pk):
    config = _get_reference_config(kind)
    instance = get_object_or_404(config['model'], pk=pk)
    form = config['form'](request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Запись обновлена.')
        return redirect('dashboard:reference_list', kind=kind)
    return render(request, 'dashboard/references/form.html', {'form': form, 'title': config['edit_title'], 'kind': kind, 'instance': instance})


@admin_required
def reference_delete(request, kind, pk):
    config = _get_reference_config(kind)
    instance = get_object_or_404(config['model'], pk=pk)
    if request.method == 'POST':
        try:
            instance.delete()
            messages.success(request, 'Запись удалена.')
        except ProtectedError:
            messages.error(request, 'Запись используется в мероприятиях и не может быть удалена.')
    return redirect('dashboard:reference_list', kind=kind)


def _get_reference_config(kind):
    if kind not in REFERENCE_CONFIG:
        raise ValueError('Неизвестный справочник')
    return REFERENCE_CONFIG[kind]
