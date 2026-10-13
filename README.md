# What Time Is It? Asks Nora

**Time awareness in Hermes, solved**

Anyone working across several threads at once knows the moment. You open Hermes in the morning, resume yesterday's conversation, and ask: "so what are we doing today?". The agent answers as if today were yesterday. Because for it, it is.

## Where it comes from

Hermes injects exactly one time anchor into context: `Conversation started: <date>`. It is attached once, at the birth of the session, and never refreshed. Resume a thread from five days ago and the model gets a five-day-old clock as its only reference point. Anything you do not type by hand gets counted against that date. "Yesterday", "by Friday", "in two weeks" all land where they land because the agent is counting from a week-old stamp.

The practical symptom is exactly the one in the title. The assistant asks what time it is. Not because it cannot check, but because nobody told it.

This is not a rare edge case or a misconfiguration. It is a documented gap: issues [#10421](https://github.com/NousResearch/hermes-agent/issues/10421) and [#54686](https://github.com/NousResearch/hermes-agent/issues/54686) in the upstream repository, a dozen pull requests, none merged as of writing. In the meantime, everyone maintaining long parallel sessions lives with it daily.

## The fix: live-time-anchor

Rather than wait for upstream, the problem is closed locally, on Hermes's official plugin API. The `pre_llm_call` hook can return context that Hermes appends to the current turn's message just before it goes to the model. One function, zero dependencies:

```python
def inject_current_time(session_id=None, user_message=None, is_first_turn=None, **kwargs):
    """pre_llm_call hook - return the live timestamp as injected context."""
    try:
        now = datetime.datetime.now().astimezone()
        zone = _zone_label()
        zone = f" ({zone})" if zone else ""
        stamp = (
            f"[CURRENT TIME - live anchor, authoritative over any earlier "
            f"session-start date in this conversation] "
            f"{now.strftime('%A')}, {now.strftime('%d %B %Y')}, {now.strftime('%H:%M')}{zone}"
        )
        return {"context": stamp}
    except Exception:
        return None  # clock problem must never break the agent turn
```

Three properties decide whether this is a fix or a band-aid:

- **Live.** The stamp is computed at every API call, not at session start. A thread resumed after a week gets today's date, not the week-old one.
- **Ephemeral.** The context exists in flight only. Session history in `state.db` stays clean, nothing duplicates or litters the database.
- **Cache-safe.** Injection goes into the user message, not the system prompt. The caching prefix at Anthropic or OpenRouter stays byte-identical between turns, so the token bill does not grow.

And the best part: it works everywhere at once. CLI, desktop, gateway, cron, kanban workers. Every turn, in every thread, resumed or fresh.

## Verification, not declaration

Following the rule that a claim without proof is marketing, three checks on a live system:

1. `hermes plugins doctor` clean: manifest parsed, import and hook registration passed.
2. A fresh Hermes process, instructed to quote the anchor from its context. Answer: `Tuesday, 13 October 2026, 12:13 (GMT Summer Time)`. The system clock in the same minute: 12:13. Agreement to the minute.
3. Database check: the user message stored in `state.db` as clean text, no anchor inside. The injection truly never reaches persistent history.

After a desktop restart the anchor shows up in every message of every resumed thread. Case closed.

## Installation

Two files, no dependencies beyond the Python standard library.

Linux / macOS:

```bash
git clone https://github.com/ErynVornTechnologies/live-time-anchor \
    ~/.hermes/plugins/live-time-anchor
hermes plugins enable live-time-anchor
```

Windows (native Hermes, HERMES_HOME in AppData):

```powershell
git clone https://github.com/ErynVornTechnologies/live-time-anchor \
    "$env:LOCALAPPDATA\hermes\plugins\live-time-anchor"
hermes plugins enable live-time-anchor
```

Then restart Hermes and that is it. Turning it off, once upstream finally merges an official fix, is one command: `hermes plugins disable live-time-anchor`.

## When will upstream fix it

Hard to say. Closest to merge is the family of PRs injecting time through user context instead of a mutable system prompt, which is exactly the architecture this plugin implements. Until then, live-time-anchor handles the problem on its own side and leaves no technical debt: no dependencies, prompt cache untouched, history clean.

---

**Licence:** [MIT](https://github.com/ErynVornTechnologies/live-time-anchor/blob/main/LICENSE). Do what you want with it.

**Author:** Kamil Nagorski, [ErynVorn Technologies](https://erynvorntechnologies.com)