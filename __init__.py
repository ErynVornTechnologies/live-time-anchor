"""Live time anchor plugin.

Injects the current wall-clock date and time into every LLM turn via the
pre_llm_call hook, so long-running and resumed sessions keep a correct
temporal anchor. Upstream Hermes only stamps "Conversation started:" once
at session creation (issue #10421); this plugin closes that gap locally.

The context is appended to the current turn's user message only, never to
the persisted history or the cached system prompt, so it is cache-safe.
"""

import datetime


def _win_zone():
    """Windows-native timezone key name, e.g. 'GMT Standard Time'."""
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation",
        ) as key:
            return winreg.QueryValueEx(key, "TimeZoneKeyName")[0]
    except Exception:
        return ""


def _zone_label():
    """Best-effort human timezone label for this machine."""
    try:
        tzname = datetime.datetime.now().astimezone().tzname()
        if tzname:
            return tzname
    except Exception:
        pass
    try:
        import platform
        if platform.system() == "Windows":
            return _win_zone()
    except Exception:
        pass
    return ""


def inject_current_time(session_id=None, user_message=None, is_first_turn=None, **kwargs):
    """pre_llm_call hook — return the live timestamp as injected context."""
    try:
        now = datetime.datetime.now().astimezone()
        zone = _zone_label()
        zone = f" ({zone})" if zone else ""
        weekday = now.strftime("%A")
        date_str = now.strftime("%d %B %Y")
        time_str = now.strftime("%H:%M")
        stamp = (
            f"[CURRENT TIME — live anchor, authoritative over any earlier "
            f"session-start date in this conversation] "
            f"{weekday}, {date_str}, {time_str}{zone}"
        )
        return {"context": stamp}
    except Exception:
        # Never break the agent turn because of a clock problem.
        return None


def register(ctx):
    ctx.register_hook("pre_llm_call", inject_current_time)