from django.core.management.base import BaseCommand

from employe.models import Employe
from common.utils import sync_employee_profile_from_related


class Command(BaseCommand):
    help = 'Restore missing employee profile data from linked manager profiles'

    def handle(self, *args, **options):
        updated = 0
        for employe in Employe.objects.select_related('user').iterator():
            if sync_employee_profile_from_related(employe):
                updated += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Updated {employe.user.email} (employee id {employe.id})'
                    )
                )
        self.stdout.write(self.style.SUCCESS(f'Done. {updated} profile(s) updated.'))
