"""Duration formatting shared by Study, Tasks (focus time) and Projects."""


def format_duration(total_seconds, style="long"):
    """Format a duration in seconds as e.g. '2h 14m' (long) or '02:14:37' (clock)."""
    total_seconds = max(0, int(total_seconds or 0))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if style == "clock":
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    if style == "compact":
        if hours:
            return f"{hours}h {minutes:02d}m"
        if minutes:
            return f"{minutes}m"
        return f"{seconds}s"

    # long
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes or hours:
        parts.append(f"{minutes}m")
    if not hours and not minutes:
        parts.append(f"{seconds}s")
    return " ".join(parts)
