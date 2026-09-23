"""Original LIFEOS icon set — geometric, single stroke-weight outline icons.

Deliberately hand-authored rather than pulled from an icon library: a small,
closed set keeps every screen visually consistent (see docs/UI_DESIGN.md,
"Iconography") and avoids depending on a CDN or vendored third-party asset
for something this central to the UI.

Usage in templates: {% icon "study" %} or {% icon "study" size=18 %}
"""

from django.template import Library
from django.utils.safestring import mark_safe

register = Library()

# Each value is the inner markup of a 24x24 viewBox, stroke="currentColor".
_ICONS = {
    "home": '<path d="M4 11.5 12 4l8 7.5"/><path d="M6 10v9a1 1 0 0 0 1 1h4v-6h2v6h4a1 1 0 0 0 1-1v-9"/>',
    "study": '<circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/>',
    "tasks": '<path d="M9 6h10M9 12h10M9 18h10"/><path d="m4 6 1.3 1.3L7.5 5"/><path d="m4 12 1.3 1.3L7.5 11"/><path d="m4 18 1.3 1.3L7.5 17"/>',
    "calendar": '<rect x="4" y="5.5" width="16" height="15" rx="2"/><path d="M4 10h16M8 3.5v3M16 3.5v3"/>',
    "projects": '<path d="M4 7.5a1.5 1.5 0 0 1 1.5-1.5H10l1.5 2H18.5A1.5 1.5 0 0 1 20 9.5V17a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 17Z"/>',
    "people": '<circle cx="9" cy="8.5" r="3"/><path d="M3.5 19c0-3 2.5-5 5.5-5s5.5 2 5.5 5"/><circle cx="17" cy="9.5" r="2.3"/><path d="M15.5 14.2c2.2.3 4 2 4 4.8"/>',
    "finance": '<rect x="3.5" y="6.5" width="17" height="12" rx="2"/><path d="M3.5 10.5h17"/><circle cx="16.5" cy="14.5" r="1.4"/>',
    "journal": '<path d="M6 4.5h9.5A2.5 2.5 0 0 1 18 7v13H8a2.5 2.5 0 0 1-2.5-2.5v-13Z"/><path d="M18 7v13"/><path d="M9 8.5h5M9 11.5h5"/>',
    "writing": '<path d="M5 19.5 5.7 16 16 5.7a1.8 1.8 0 0 1 2.5 0l0 0a1.8 1.8 0 0 1 0 2.5L8.2 18.5Z"/><path d="M14 7.7 16.3 10"/>',
    "goals": '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4.2"/><circle cx="12" cy="12" r="0.6" fill="currentColor"/>',
    "notes": '<path d="M6 4.5h12v11L13 20H6Z"/><path d="M13 15.3V20l5-4.7Z"/><path d="M9 8.5h6M9 11.5h6"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6"/><path d="m19 19-4.3-4.3"/>',
    "devices": '<rect x="3.5" y="5.5" width="13" height="9" rx="1.4"/><path d="M8 18.5h6"/><rect x="17.5" y="9.5" width="4" height="7.5" rx="1"/>',
    "settings": '<circle cx="12" cy="12" r="2.7"/><path d="M12 3.5v2.2M12 18.3v2.2M20.5 12h-2.2M5.7 12H3.5M17.8 6.2l-1.55 1.55M7.75 16.25 6.2 17.8M17.8 17.8l-1.55-1.55M7.75 7.75 6.2 6.2"/>',
    "inbox": '<path d="M4 12.5h4.2l1.3 2.5h5l1.3-2.5H20"/><path d="M5.2 6.5h13.6L20 12.5v5A1.5 1.5 0 0 1 18.5 19h-13A1.5 1.5 0 0 1 4 17.5v-5Z"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "chevron-right": '<path d="m9 6 6 6-6 6"/>',
    "chevron-left": '<path d="m15 6-6 6 6 6"/>',
    "x": '<path d="m6 6 12 12M18 6 6 18"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7"/>',
    "play": '<path d="M7 5.5v13l11-6.5Z"/>',
    "pause": '<path d="M7.5 5.5h3v13h-3ZM13.5 5.5h3v13h-3Z"/>',
    "stop": '<rect x="6" y="6" width="12" height="12" rx="1.5"/>',
    "more-horizontal": '<circle cx="5.5" cy="12" r="1.3" fill="currentColor"/><circle cx="12" cy="12" r="1.3" fill="currentColor"/><circle cx="18.5" cy="12" r="1.3" fill="currentColor"/>',
    "arrow-right": '<path d="M4 12h16M13 6l6 6-6 6"/>',
    "clock": '<circle cx="12" cy="12" r="8"/><path d="M12 7.5V12l3 2"/>',
    "flag": '<path d="M6 4v16"/><path d="M6 5h10l-2.2 3.5L16 12H6Z"/>',
    "folder": '<path d="M4 7a1.5 1.5 0 0 1 1.5-1.5H10l1.5 2H18.5A1.5 1.5 0 0 1 20 9v8a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 17Z"/>',
    "briefcase": '<rect x="3.5" y="8" width="17" height="11" rx="1.6"/><path d="M8.5 8V6.2A1.7 1.7 0 0 1 10.2 4.5h3.6A1.7 1.7 0 0 1 15.5 6.2V8"/><path d="M3.5 13h17"/>',
    "wallet": '<path d="M4 7.5A1.5 1.5 0 0 1 5.5 6h11A1.5 1.5 0 0 1 18 7.5V9h1.5A1.5 1.5 0 0 1 21 10.5v6A1.5 1.5 0 0 1 19.5 18h-14A1.5 1.5 0 0 1 4 16.5Z"/><circle cx="16.3" cy="13.7" r="1.2" fill="currentColor"/>',
    "book": '<path d="M6 4.5h9.5A2.5 2.5 0 0 1 18 7v13H8a2.5 2.5 0 0 1-2.5-2.5v-13Z"/><path d="M18 7v13"/>',
    "target": '<circle cx="12" cy="12" r="7.5"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="0.6" fill="currentColor"/>',
    "bell": '<path d="M7 10a5 5 0 0 1 10 0c0 4 1.5 5 1.5 5h-13S7 14 7 10Z"/><path d="M10.3 18a1.8 1.8 0 0 0 3.4 0"/>',
    "sync": '<path d="M5 12a7 7 0 0 1 11.5-5.3M19 12a7 7 0 0 1-11.5 5.3"/><path d="M16 4.5v3h-3M8 19.5v-3h3"/>',
    "qr": '<rect x="4" y="4" width="6" height="6" rx="1"/><rect x="14" y="4" width="6" height="6" rx="1"/><rect x="4" y="14" width="6" height="6" rx="1"/><path d="M14 14h2.5v2.5H14ZM19 14v2.5M14 19h2.5M19 19v0h.01"/>',
    "trash": '<path d="M5 7.5h14M9.5 7.5V6a1.5 1.5 0 0 1 1.5-1.5h2A1.5 1.5 0 0 1 14.5 6v1.5"/><path d="M7 7.5 7.7 18a1.6 1.6 0 0 0 1.6 1.5h5.4a1.6 1.6 0 0 0 1.6-1.5l0.7-10.5Z"/>',
    "edit": '<path d="M6 18.5 6.5 15.3 15.4 6.4a1.7 1.7 0 0 1 2.4 0l0 0a1.7 1.7 0 0 1 0 2.4L8.9 18Z"/>',
    "filter": '<path d="M4 5.5h16L14 13v5.5l-4 2V13Z"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 3.5v2M12 18.5v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M3.5 12h2M18.5 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "moon": '<path d="M20 14.2A8 8 0 1 1 9.8 4a6.4 6.4 0 0 0 10.2 10.2Z"/>',
    "monitor": '<rect x="3.5" y="5" width="17" height="11" rx="1.5"/><path d="M9 19.5h6M12 16v3.5"/>',
    "card": '<rect x="3.5" y="6" width="17" height="12" rx="2"/><path d="M3.5 10h17"/><path d="M6.5 14h4"/>',
    "transfer": '<path d="M4 8h13M17 8l-3-3M17 8l-3 3"/><path d="M20 16H7M7 16l3-3M7 16l3 3"/>',
    "streak": '<path d="M12 21c4 0 6.5-2.7 6.5-6.2 0-3.2-2.2-5-3.4-7.3-.5 1.8-1.6 2.7-2.4 2-1-.9-.9-3-.2-4.5C9.8 6.4 7.5 9 7.5 12.8 7.5 18.3 8 21 12 21Z"/>',
    "external": '<path d="M9 6H6.5A1.5 1.5 0 0 0 5 7.5v10A1.5 1.5 0 0 0 6.5 19h10a1.5 1.5 0 0 0 1.5-1.5V15"/><path d="M13 4.5h6.5V11M19.3 4.7 11 13"/>',
    "download": '<path d="M12 4v11M8 11.5 12 15.5 16 11.5"/><path d="M5 18.5h14"/>',
    "upload": '<path d="M12 20V9M8 12.5 12 8.5 16 12.5"/><path d="M5 18.5h14"/>',
    "shield": '<path d="M12 4 5.5 6.5V12c0 4.4 2.8 6.8 6.5 8 3.7-1.2 6.5-3.6 6.5-8V6.5Z"/><path d="m9.3 12 1.9 1.9 3.5-3.8"/>',
    "warning": '<path d="M12 4.5 21 19.5H3Z"/><path d="M12 10v4"/><circle cx="12" cy="16.7" r="0.6" fill="currentColor"/>',
    "info": '<circle cx="12" cy="12" r="8"/><path d="M12 11v5.5"/><circle cx="12" cy="8" r="0.6" fill="currentColor"/>',
    "refresh": '<path d="M4.5 12a7.5 7.5 0 0 1 12.6-5.5M19.5 12a7.5 7.5 0 0 1-12.6 5.5"/><path d="M17 4.5v3.5h-3.5M7 19.5V16h3.5"/>',
    "sparkle": '<path d="M12 4c.4 3 1.6 4.6 5 5.5-3.4.9-4.6 2.5-5 5.5-.4-3-1.6-4.6-5-5.5C10.4 8.6 11.6 7 12 4Z"/><path d="M19 15.5c.2 1.3.7 2 2 2.3-1.3.3-1.8 1-2 2.3-.2-1.3-.7-2-2-2.3 1.3-.3 1.8-1 2-2.3Z"/>',
    "layers": '<path d="m12 4 8 4.3-8 4.3-8-4.3Z"/><path d="m4 13 8 4.3 8-4.3"/>',
    "menu": '<path d="M4 6.5h16M4 12h16M4 17.5h16"/>',
}


@register.simple_tag
def icon(name, size=16, cls=""):
    body = _ICONS.get(name)
    if body is None:
        body = _ICONS["sparkle"]
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" '
        f'stroke-linecap="round" stroke-linejoin="round" class="icon {cls}">{body}</svg>'
    )
    return mark_safe(svg)
