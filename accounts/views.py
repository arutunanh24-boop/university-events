from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render

from events.models import Notification, Registration

from .forms import EmailAuthenticationForm, ProfileForm, UserRegistrationForm


class CourseworkLoginView(LoginView):
    authentication_form = EmailAuthenticationForm
    template_name = 'registration/login.html'


class CourseworkLogoutView(LogoutView):
    pass


def register(request):
    if request.user.is_authenticated:
        return redirect('accounts:profile')
    form = UserRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Регистрация выполнена. Добро пожаловать!')
        return redirect('accounts:profile')
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Профиль обновлен.')
        return redirect('accounts:profile')

    registrations = (
        Registration.objects.filter(user=request.user)
        .select_related('event', 'event__category', 'event__location')
        .order_by('-registered_at')[:5]
    )
    unread_notifications = Notification.objects.filter(user=request.user, is_read=False).count()
    return render(
        request,
        'accounts/profile.html',
        {
            'form': form,
            'registrations': registrations,
            'unread_notifications': unread_notifications,
        },
    )
