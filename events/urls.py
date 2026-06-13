from django.urls import path

from . import views

app_name = 'events'

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('events/<int:pk>/', views.event_detail, name='event_detail'),
    path('events/create/', views.event_create, name='event_create'),
    path('events/<int:pk>/edit/', views.event_edit, name='event_edit'),
    path('events/<int:pk>/delete/', views.event_delete, name='event_delete'),
    path('events/<int:pk>/register/', views.register_for_event, name='register_for_event'),
    path('events/<int:pk>/cancel-registration/', views.cancel_registration, name='cancel_registration'),
    path('events/<int:pk>/participants/', views.participant_list, name='participants'),
    path('events/<int:pk>/participants/csv/', views.export_participants_csv, name='export_participants_csv'),
    path('events/<int:pk>/participants/xlsx/', views.export_participants_xlsx, name='export_participants_xlsx'),
    path('events/<int:pk>/files/upload/', views.upload_event_file, name='upload_event_file'),
    path('files/<int:pk>/delete/', views.delete_event_file, name='delete_event_file'),
    path('events/<int:pk>/comments/add/', views.add_comment, name='add_comment'),
    path('my-registrations/', views.my_registrations, name='my_registrations'),
    path('notifications/', views.notifications, name='notifications'),
]
