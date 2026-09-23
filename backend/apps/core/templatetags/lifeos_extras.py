import markdown as markdown_lib
from django import template
from django.utils.safestring import mark_safe

from apps.core.durations import format_duration
from apps.core.money import format_money

register = template.Library()


@register.filter
def render_markdown(text):
    """Renders the owner's own local notes/journal content. There is no
    multi-user or public-content path in LIFEOS (spec §97, single owner) —
    the trust boundary here is the same as a local Markdown editor's."""
    if not text:
        return ""
    return mark_safe(markdown_lib.markdown(text, extensions=["extra", "sane_lists"]))


@register.filter
def money(amount, currency="MAD"):
    return format_money(amount, currency)


@register.filter
def duration(total_seconds, style="long"):
    return format_duration(total_seconds, style)


@register.filter
def duration_compact(total_seconds):
    return format_duration(total_seconds, "compact")


@register.filter
def initials(name):
    if not name:
        return ""
    parts = str(name).strip().split()
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


@register.filter
def percent(value, total):
    try:
        value = float(value)
        total = float(total)
    except (TypeError, ValueError):
        return 0
    if total <= 0:
        return 0
    return round(min(100, max(0, (value / total) * 100)))


@register.filter
def get_item(d, key):
    if d is None:
        return None
    return d.get(key)
