from django.core.management.base import BaseCommand, CommandError

from apps.core.backup import RestoreError, list_backups, restore_backup


class Command(BaseCommand):
    help = "Restores the database from a backup file in backups/. Creates a safety backup of the current state first."

    def add_arguments(self, parser):
        parser.add_argument("filename", nargs="?", help="Backup filename (default: most recent)")

    def handle(self, *args, **options):
        filename = options.get("filename")
        if not filename:
            backups = list_backups()
            if not backups:
                raise CommandError("No backups found in backups/.")
            filename = backups[0].filename

        try:
            safety = restore_backup(filename)
        except RestoreError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(f"Restored from {filename}. Safety backup of the prior state: {safety.filename}"))
