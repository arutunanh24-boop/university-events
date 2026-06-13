from django.db.models import Count, Q

from .models import Event, Notification, Registration


def can_manage_event(user, event: Event) -> bool:
    if not user.is_authenticated:
        return False
    return user.is_coursework_admin or event.organizer_id == user.id


def notify_registered_participants(event: Event, notification_type: str, title: str, message: str) -> int:
    registrations = event.registrations.filter(status=Registration.Status.REGISTERED).select_related('user')
    notifications = [
        Notification(
            user=registration.user,
            event=event,
            title=title,
            message=message,
            notification_type=notification_type,
        )
        for registration in registrations
    ]
    Notification.objects.bulk_create(notifications)
    return len(notifications)


def event_statistics_queryset(queryset=None):
    source = queryset or Event.objects.all()
    return source.annotate(
        registered_total=Count(
            'registrations',
            filter=Q(registrations__status=Registration.Status.REGISTERED),
        )
    )
