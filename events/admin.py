from django.contrib import admin

from .models import Category, Comment, Event, EventFile, Location, Notification, Registration, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'building', 'room')
    search_fields = ('name', 'building', 'room', 'address')


class EventFileInline(admin.TabularInline):
    model = EventFile
    extra = 0


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'start_datetime', 'category', 'organizer', 'registered_count')
    list_filter = ('status', 'category', 'organization')
    search_fields = ('title', 'description')
    filter_horizontal = ('tags',)
    inlines = [EventFileInline]


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'status', 'registered_at')
    list_filter = ('status', 'event')
    search_fields = ('user__email', 'event__title')


@admin.register(EventFile)
class EventFileAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'event', 'file_type', 'uploaded_by', 'uploaded_at')
    list_filter = ('file_type',)
    search_fields = ('file_name', 'event__title')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'event', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('title', 'message', 'user__email', 'event__title')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'comment_type', 'created_at')
    list_filter = ('comment_type',)
    search_fields = ('content', 'user__email', 'event__title')
