from django.core.management.base import BaseCommand

from apps.core.backup import create_backup


class Command(BaseCommand):
    help = "Creates a timestamped local backup of the LIFEOS database under backups/."

    def handle(self, *args, **options):
        backup = create_backup()
        self.stdout.write(self.style.SUCCESS(f"Backup created: {backup.path} ({backup.size_mb} MB)"))
