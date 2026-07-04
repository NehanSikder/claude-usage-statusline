# claude-usage-statusline

**Problem:** Claude Code gives you no always-on warning before you hit a rate
limit — you only find out when you're already blocked mid-task, with no sense of
how close you were or when it resets.

This adds a self-documenting, bottom-docked status line that answers *"how close
am I to being rate limited?"* at a glance — no glyphs to memorize.

```
Claude usage limits  (Opus)
5-hour    █████░░░░░  46% used  · resets in 3h48m
weekly    ██░░░░░░░░  23% used  · resets in 19h08m
context   ██░░░░░░░░  44k / 200k (22%)  · normal rate limit ✓
```

Every label spells out what it means, so a teammate can read it cold.

## What each line means

| Line | Meaning |
|------|---------|
| **5-hour** | Your rolling 5-hour usage window (the one that resets most often). |
| **weekly** | Your 7-day usage window. |
| **context** | How full the current session's context is. Because every message re-sends the whole context, a bigger context drains your rate limit faster — the note escalates `normal → fast → faster rate limit` and suggests `/compact` or `/clear`. |

Colors: green under 50%, yellow 50–80%, red above 80% (context tiers at 150k / 180k).

## Requirements

- **Claude Code**, logged in on a Claude subscription (Pro/Max). The 5-hour and
  weekly lines read Anthropic's official rate-limit headers.
- **Python 3** (used by the status line and the installer — no other deps).

That's it. No `jq`, no Node.

## Install

```bash
git clone https://github.com/<you>/claude-usage-statusline
cd claude-usage-statusline
./install.sh
```

Then restart (or open a new) Claude Code session.

The installer is **non-destructive**: it backs up your `~/.claude/settings.json`
and merges in *only* the `statusLine` block — your model, plugins, and other
settings are left untouched.

### First run
On a brand-new session the 5-hour/weekly lines may briefly show `no data yet`
until `cs` sees its first API response. This is normal.

## Uninstall

```bash
./install.sh --uninstall
```

Removes the two files and restores your `settings.json` backup.

## How it works

- [`claude-statusbar`](https://pypi.org/project/claude-statusbar/) (the `cs`
  binary) provides the raw rate-limit numbers from Anthropic's headers.
- `statusline-usage.py` wraps it, adds a live **context** gauge computed from the
  session transcript, and prints everything with plain-English labels.
- `claude-statusbar.json` is a decluttered `cs` config (cost/balance/todos/etc.
  turned off) so nothing competes with the rate-limit signal.

## Scope / caveats

- The **rate-limit** lines are Claude-subscription-specific. On other providers
  they won't show meaningful data (the context gauge still works for any model).
- The **context** gauge assumes a 200k window and reads the last main-chain
  turn's tokens from the transcript, sidestepping Claude Code's cumulative
  `context_window` bug (issue #13783).
