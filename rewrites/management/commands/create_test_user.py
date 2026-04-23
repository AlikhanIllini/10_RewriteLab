"""
Create or reset the A10 test user (mohitg2 / uiuc12345).

Safe to run multiple times. If the user already exists, the password
is reset to the expected value.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or reset the A10 grader test user."

    def handle(self, *args, **opts):
        User = get_user_model()
        username = 'mohitg2'
        password = 'uiuc12345'
        email = 'mohitg2@illinois.edu'

        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email, 'first_name': 'Mohit', 'last_name': 'G'},
        )
        user.email = email
        user.set_password(password)
        user.is_active = True
        user.save()

        action = 'Created' if created else 'Reset password for'
        self.stdout.write(self.style.SUCCESS(
            f"{action} test user: {username} / {password}"
        ))
