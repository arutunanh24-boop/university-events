from datetime import timedelta

from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Organization, User
from events.models import Category, Comment, Event, EventFile, Location, Notification, Registration, Tag


class Command(BaseCommand):
    help = 'Creates demonstration users, reference data, events and registrations.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete demo data before loading it.')

    def handle(self, *args, **options):
        if options['reset']:
            self._reset_demo_data()
        self._create_groups()
        organizations = self._create_organizations()
        categories = self._create_categories()
        tags = self._create_tags()
        locations = self._create_locations()
        users = self._create_users(organizations)
        events = self._create_events(categories, tags, locations, organizations, users)
        self._create_registrations(events, users)
        self._create_comments(events, users)
        self._create_notifications(events, users)
        self._create_files(events, users)
        self.stdout.write(self.style.SUCCESS('Demo data loaded.'))

    def _reset_demo_data(self):
        EventFile.objects.all().delete()
        Comment.objects.all().delete()
        Notification.objects.all().delete()
        Registration.objects.all().delete()
        Event.objects.all().delete()
        Category.objects.all().delete()
        Tag.objects.all().delete()
        Location.objects.all().delete()
        Organization.objects.all().delete()
        User.objects.filter(email__in=['admin@example.com', 'organizer@example.com', 'student@example.com']).delete()

    def _create_groups(self):
        for role, label in User.Role.choices:
            Group.objects.get_or_create(name=label)

    def _create_organizations(self):
        data = [
            ('Факультет информационных технологий', Organization.FACULTY, 'Учебное подразделение, проводящее IT-события.'),
            ('Кафедра прикладной информатики', Organization.DEPARTMENT, 'Кафедра организует лекции, семинары и практикумы.'),
            ('Студенческий совет', Organization.UNION, 'Объединение для студенческих инициатив.'),
            ('Волонтерский центр', Organization.CLUB, 'Команда социальных и добровольческих проектов.'),
        ]
        result = {}
        for name, org_type, description in data:
            org, _ = Organization.objects.update_or_create(
                name=name,
                defaults={'type': org_type, 'description': description},
            )
            result[name] = org
        return result

    def _create_categories(self):
        names = {
            'Научное': 'Конференции, круглые столы и исследовательские встречи.',
            'Образовательное': 'Лекции, мастер-классы, интенсивы и семинары.',
            'Культурное': 'Творческие вечера, встречи и концерты.',
            'Спортивное': 'Турниры, соревнования и тренировки.',
            'Профориентационное': 'Дни карьеры и встречи с работодателями.',
            'Волонтерское': 'Социальные и добровольческие мероприятия.',
        }
        return {
            name: Category.objects.update_or_create(name=name, defaults={'description': description})[0]
            for name, description in names.items()
        }

    def _create_tags(self):
        names = ['IT', 'карьера', 'наука', 'спорт', 'волонтерство', 'мастер-класс', 'студенты', 'лекция']
        return {name: Tag.objects.get_or_create(name=name)[0] for name in names}

    def _create_locations(self):
        data = [
            ('Актовый зал', 'Главный корпус', '101', 'ул. Университетская, 1'),
            ('IT-лаборатория', 'Корпус Б', '304', 'ул. Университетская, 3'),
            ('Конференц-зал', 'Корпус А', '212', 'ул. Университетская, 1'),
            ('Спортивный зал', 'Спорткомплекс', '1', 'ул. Спортивная, 5'),
            ('Коворкинг', 'Корпус В', '110', 'ул. Университетская, 7'),
        ]
        result = {}
        for name, building, room, address in data:
            location, _ = Location.objects.update_or_create(
                name=name,
                building=building,
                room=room,
                defaults={'address': address, 'description': 'Площадка университета для проведения мероприятий.'},
            )
            result[name] = location
        return result

    def _create_users(self, organizations):
        users = {
            'admin': self._upsert_user(
                'admin@example.com',
                'Администратор',
                'Системный',
                '',
                User.Role.ADMIN,
                organizations['Факультет информационных технологий'],
                is_staff=True,
                is_superuser=True,
            ),
            'organizer': self._upsert_user(
                'organizer@example.com',
                'Иванов',
                'Петр',
                'Сергеевич',
                User.Role.ORGANIZER,
                organizations['Кафедра прикладной информатики'],
                is_staff=False,
                is_superuser=False,
            ),
            'student': self._upsert_user(
                'student@example.com',
                'Арутюнян',
                'Анна',
                'Робертовна',
                User.Role.STUDENT,
                organizations['Факультет информационных технологий'],
                is_staff=False,
                is_superuser=False,
            ),
        }
        for user in users.values():
            group_name = dict(User.Role.choices)[user.role]
            group = Group.objects.get(name=group_name)
            user.groups.set([group])
        return users

    def _upsert_user(self, email, last_name, first_name, middle_name, role, organization, is_staff, is_superuser):
        user, created = User.objects.update_or_create(
            email=email,
            defaults={
                'last_name': last_name,
                'first_name': first_name,
                'middle_name': middle_name,
                'role': role,
                'organization': organization,
                'is_active': True,
                'is_staff': is_staff,
                'is_superuser': is_superuser,
            },
        )
        if created or not user.has_usable_password():
            user.set_password('demo12345')
            user.save()
        return user

    def _create_events(self, categories, tags, locations, organizations, users):
        now = timezone.now()
        data = [
            ('Открытая лекция по веб-разработке', 'Образовательное', 'IT-лаборатория', 3, 24, ['IT', 'лекция', 'студенты']),
            ('Научная конференция молодых исследователей', 'Научное', 'Конференц-зал', 7, 80, ['наука', 'студенты']),
            ('Мастер-класс по Django', 'Образовательное', 'IT-лаборатория', 10, 20, ['IT', 'мастер-класс']),
            ('День карьеры в IT', 'Профориентационное', 'Актовый зал', 14, 120, ['IT', 'карьера']),
            ('Волонтерский сбор проектов', 'Волонтерское', 'Коворкинг', 5, 35, ['волонтерство', 'студенты']),
            ('Университетский турнир по волейболу', 'Спортивное', 'Спортивный зал', 12, 50, ['спорт', 'студенты']),
            ('Творческий вечер студенческих объединений', 'Культурное', 'Актовый зал', 16, 100, ['студенты']),
            ('Архивный семинар по анализу данных', 'Научное', 'Конференц-зал', -5, 30, ['наука', 'IT']),
        ]
        result = []
        for title, category_name, location_name, day_shift, limit, tag_names in data:
            start = now + timedelta(days=day_shift, hours=2)
            end = start + timedelta(hours=2)
            status = Event.Status.COMPLETED if day_shift < 0 else Event.Status.PUBLISHED
            event, _ = Event.objects.update_or_create(
                title=title,
                defaults={
                    'description': (
                        'Мероприятие проводится внутри университета и включает регистрацию участников, '
                        'организационную информацию и последующую обработку данных.'
                    ),
                    'start_datetime': start,
                    'end_datetime': end,
                    'status': status,
                    'max_participants': limit,
                    'category': categories[category_name],
                    'location': locations[location_name],
                    'organizer': users['organizer'],
                    'organization': organizations['Кафедра прикладной информатики'],
                },
            )
            event.tags.set([tags[name] for name in tag_names])
            result.append(event)
        return result

    def _create_registrations(self, events, users):
        student = users['student']
        admin = users['admin']
        for event in events[:5]:
            Registration.objects.update_or_create(
                user=student,
                event=event,
                defaults={'status': Registration.Status.REGISTERED},
            )
        for event in events[1:4]:
            Registration.objects.update_or_create(
                user=admin,
                event=event,
                defaults={'status': Registration.Status.REGISTERED},
            )
        Registration.objects.update_or_create(
            user=student,
            event=events[-1],
            defaults={'status': Registration.Status.CANCELLED},
        )

    def _create_comments(self, events, users):
        Comment.objects.update_or_create(
            user=users['student'],
            event=events[0],
            content='Будет ли запись лекции доступна после мероприятия?',
            defaults={'comment_type': Comment.Type.COMMENT},
        )
        Comment.objects.update_or_create(
            user=users['student'],
            event=events[-1],
            content='Полезный семинар, особенно часть с практическими примерами.',
            defaults={'comment_type': Comment.Type.REVIEW},
        )

    def _create_notifications(self, events, users):
        Notification.objects.update_or_create(
            user=users['student'],
            event=events[0],
            title='Обновлена информация о мероприятии',
            defaults={
                'message': 'Организатор уточнил программу открытой лекции.',
                'notification_type': Notification.Type.CHANGED,
                'is_read': False,
            },
        )

    def _create_files(self, events, users):
        if events[0].files.exists():
            return
        files = [
            (events[0], 'program_lecture.txt', EventFile.FileType.PROGRAM, 'Программа открытой лекции по веб-разработке.'),
            (events[2], 'django_workshop_rules.txt', EventFile.FileType.REGULATION, 'Положение о мастер-классе по Django.'),
        ]
        for event, filename, file_type, content in files:
            event_file = EventFile(event=event, uploaded_by=users['organizer'], file_type=file_type)
            event_file.file.save(filename, ContentFile(content.encode('utf-8')), save=True)
