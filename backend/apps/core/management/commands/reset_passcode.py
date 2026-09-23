import getpass

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from apps.core.models import log_activity


class Command(BaseCommand):
    """Local-only passcode recovery for a forgotten LIFEOS passcode.

    Deliberately NOT an HTTP endpoint, token, or flag reachable over the
    network or from within the app's own login screen — the only way to
    invoke this is shell/filesystem access to the machine LIFEOS runs on,
    which is the same trust level required to read the SQLite file directly.
    It goes through the exact same User.set_password() hashing path as a
    normal in-app passcode change, so it can't weaken or bypass the login
    check itself. The reset is logged to the in-app activity feed so a
    reset is never invisible to the owner.
    """

    help = "Recover access by resetting the local owner's passcode. Requires interactive confirmation."

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username="owner")
        except User.DoesNotExist:
            raise CommandError("No LIFEOS owner account exists yet — run first-run setup instead.")

        self.stdout.write(self.style.WARNING(
            "This resets the LIFEOS passcode for this device's owner account.\n"
            "Anyone who can run this command already has full filesystem access to your LIFEOS data."
        ))
        confirm = input('Type "RESET" to continue: ')
        if confirm != "RESET":
            self.stdout.write("Aborted. Passcode was not changed.")
            return

        new_password = getpass.getpass("New passcode: ")
        if len(new_password) < 4:
            raise CommandError("Passcode must be at least 4 characters.")
        confirm_password = getpass.getpass("Confirm new passcode: ")
        if new_password != confirm_password:
            raise CommandError("Passcodes didn't match. Nothing was changed.")

        user.set_password(new_password)
        user.save()
        log_activity("Passcode was reset via local recovery command", category="system")

        self.stdout.write(self.style.SUCCESS("Passcode reset. All existing sessions on other devices remain signed in until they log out."))
