from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.CourseworkLoginView.as_view(), name='login'),
    path('logout/', views.CourseworkLogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
]
