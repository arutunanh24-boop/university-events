from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/', views.user_detail, name='user_detail'),
    path('users/<int:pk>/edit/', views.user_update, name='user_update'),
    path('users/<int:pk>/deactivate/', views.user_deactivate, name='user_deactivate'),
    path('references/<str:kind>/', views.reference_list, name='reference_list'),
    path('references/<str:kind>/create/', views.reference_create, name='reference_create'),
    path('references/<str:kind>/<int:pk>/edit/', views.reference_update, name='reference_update'),
    path('references/<str:kind>/<int:pk>/delete/', views.reference_delete, name='reference_delete'),
]
