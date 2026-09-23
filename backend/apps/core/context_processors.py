from django.conf import settings

from apps.core.models import Profile


def lifeos_context(request):
    profile = None
    inbox_unprocessed_count = 0
    if request.user.is_authenticated:
        profile = Profile.objects.filter(user=request.user).first()
        from apps.inbox.models import InboxItem

        inbox_unprocessed_count = InboxItem.objects.filter(processed=False).count()

    return {
        "lifeos_version": settings.LIFEOS_VERSION,
        "lifeos_profile": profile,
        "lifeos_theme": profile.theme if profile else "system",
        "lifeos_currency": profile.default_currency if profile else settings.LIFEOS_DEFAULT_CURRENCY,
        "inbox_unprocessed_count": inbox_unprocessed_count,
    }
