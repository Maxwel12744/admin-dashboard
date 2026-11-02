from django.core.management.base import BaseCommand

from dashboard.reminders import create_due_reminders


class Command(BaseCommand):
    help = "Create 'due soon' and 'overdue' notifications for everyone. Run it on a schedule."

    def handle(self, *args, **options):
        created = create_due_reminders()
        self.stdout.write(self.style.SUCCESS(f"{created} reminder(s) created."))
