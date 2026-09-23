from rest_framework import authentication, exceptions

from apps.devices.models import DeviceCredential


class DeviceTokenAuthentication(authentication.BaseAuthentication):
    """Authenticates Android (or any non-desktop) API clients via a per-device
    bearer token: ``Authorization: Device <token>``.

    On success, ``request.user`` is the single LIFEOS owner (auth is single
    user; the token identifies *which device* is acting) and
    ``request.auth`` is the Device instance, so views can still tell devices
    apart for sync bookkeeping.
    """

    keyword = "Device"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()
        if not header or header[0].decode().lower() != self.keyword.lower():
            return None
        if len(header) != 2:
            raise exceptions.AuthenticationFailed("Malformed Device token header.")

        raw_token = header[1].decode()
        device = DeviceCredential.authenticate(raw_token)
        if device is None:
            raise exceptions.AuthenticationFailed("Invalid or revoked device token.")

        device.touch()
        owner = _owner_user()
        if owner is None:
            raise exceptions.AuthenticationFailed("LIFEOS has not completed first-run setup yet.")
        return (owner, device)

    def authenticate_header(self, request):
        return self.keyword


def _owner_user():
    from django.contrib.auth.models import User

    return User.objects.filter(is_superuser=False, lifeos_profile__isnull=False).first() or User.objects.first()


def request_device(request):
    """request.auth is the Device instance under DeviceTokenAuthentication
    (Android/other clients) and None under SessionAuthentication (desktop)."""
    return request.auth if hasattr(request.auth, "platform") else None
