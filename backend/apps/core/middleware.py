import time

from django.contrib.auth import logout
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

LAST_ACTIVITY_SESSION_KEY = "_lifeos_last_activity"

# Paths that poll in the background (session-status ticks, pairing-code
# checks) must never count as "activity" — spec: auto-lock counts only
# mouse/keyboard/nav/interaction, never background polling/sync/timers.
# They are still subject to the lock itself; they just never refresh it.
POLLING_PATH_MARKER = "/status/"

EXEMPT_PATH_PREFIXES = ("/static/", "/media/")


class AutoLockMiddleware:
    """Bank-level inactivity auto-lock.

    Any authenticated, non-polling request refreshes a last-activity
    timestamp in the session. Once the gap since that timestamp exceeds the
    owner's configured Profile.auto_lock_minutes, the next request of any
    kind is force-logged-out and bounced to the lock screen — closing the
    single window where a background poll could keep serving data to an
    already-"locked" tab.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.path.startswith(EXEMPT_PATH_PREFIXES):
            is_polling = POLLING_PATH_MARKER in request.path
            last_activity = request.session.get(LAST_ACTIVITY_SESSION_KEY)

            if last_activity is not None:
                profile = getattr(request.user, "lifeos_profile", None)
                limit_minutes = profile.auto_lock_minutes if profile else 10
                if time.time() - last_activity >= limit_minutes * 60:
                    logout(request)
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return JsonResponse({"active": False, "locked": True}, status=401)
                    return redirect(f"{reverse('core:login')}?locked=1")

            if not is_polling:
                request.session[LAST_ACTIVITY_SESSION_KEY] = time.time()

        return self.get_response(request)
