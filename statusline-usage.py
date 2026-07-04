#!/usr/bin/env python3
"""Self-documenting Claude Code rate-limit + context status line.

Reads Claude Code's session JSON on stdin, asks `claude-statusbar` for the raw
rate-limit numbers (--json-output), and computes current context occupancy from
the transcript. Prints an explicitly-labeled bar so anyone can glance at it and
understand it with zero prior knowledge.
"""
import os
import sys
import json
import shutil
import subprocess

# `cs` (claude-statusbar) is resolved from PATH so this works on any machine.
# Falls back to the common pip --user location if it's not on PATH.
CS = shutil.which("cs") or os.path.expanduser(
    "~/Library/Python/3.9/bin/cs"
)
WARN, CRIT = 50, 80              # % of a rate-limit window: green->yellow->red
CONTEXT_WINDOW = 200_000        # Opus/Sonnet standard context window
CONTEXT_WARN = 150_000          # the "longer sessions get expensive" threshold
CONTEXT_HOT = 180_000           # approaching the window ceiling

# ANSI colors (Claude Code renders these in the status line)
GREEN = "\033[38;5;114m"
YELLOW = "\033[38;5;179m"
RED = "\033[38;5;203m"
DIM = "\033[38;5;244m"
RESET = "\033[0m"


def pct_color(pct: float) -> str:
    if pct >= CRIT:
        return RED
    if pct >= WARN:
        return YELLOW
    return GREEN


def bar(pct: float, width: int = 10) -> str:
    filled = max(0, min(width, round(pct / 100 * width)))
    return "█" * filled + "░" * (width - filled)


def limit_line(label: str, seg: dict) -> str:
    pct = seg.get("used_percentage")
    reset = seg.get("reset_time", "?")
    if pct is None:
        return f"{DIM}{label:<10}no data yet{RESET}"
    c = pct_color(pct)
    return (
        f"{DIM}{label:<10}{RESET}"
        f"{c}{bar(pct)} {pct:>3.0f}% used{RESET}  "
        f"{DIM}· resets in {reset}{RESET}"
    )


def current_context(transcript_path: str):
    """Current context occupancy = last main-chain turn's input+cache tokens.

    Avoids Claude Code's buggy cumulative context_window field (issue #13783).
    """
    last = None
    try:
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                if ev.get("type") == "assistant" and not ev.get("isSidechain", False):
                    u = ev.get("message", {}).get("usage")
                    if u:
                        last = u
    except (FileNotFoundError, OSError):
        return None
    if not last:
        return None
    return (
        last.get("input_tokens", 0)
        + last.get("cache_read_input_tokens", 0)
        + last.get("cache_creation_input_tokens", 0)
    )


def context_line(transcript_path: str) -> str:
    ctx = current_context(transcript_path)
    if ctx is None:
        return f"{DIM}{'context':<10}n/a{RESET}"
    pct = ctx / CONTEXT_WINDOW * 100
    if ctx >= CONTEXT_HOT:
        c, note = RED, "⚠ faster rate limit · /compact or /clear"
    elif ctx >= CONTEXT_WARN:
        c, note = YELLOW, "⚠ fast rate limit · /compact"
    else:
        c, note = GREEN, "normal rate limit ✓"
    return (
        f"{DIM}{'context':<10}{RESET}"
        f"{c}{bar(pct)} {ctx / 1000:.0f}k / {CONTEXT_WINDOW // 1000}k ({pct:.0f}%){RESET}  "
        f"{DIM}· {note}{RESET}"
    )


def main() -> None:
    stdin = sys.stdin.read()

    # Rate-limit data from claude-statusbar (official headers).
    try:
        out = subprocess.run(
            [CS, "--json-output", "--no-auto-update"],
            input=stdin, capture_output=True, text=True, timeout=5,
        )
        data = json.loads(out.stdout)
    except Exception:
        data = {}

    # Session context: transcript path comes from Claude Code's stdin JSON.
    try:
        session = json.loads(stdin)
    except ValueError:
        session = {}
    transcript_path = session.get("transcript_path", "")
    model = data.get("meta", {}).get("display_name", "") or (
        session.get("model", {}).get("display_name", "")
    )

    rl = data.get("rate_limits", {})
    header = f"{DIM}Claude usage limits{RESET}"
    if model:
        header += f"  {DIM}({model}){RESET}"
    print(header)
    print(limit_line("5-hour", rl.get("five_hour", {})))
    print(limit_line("weekly", rl.get("seven_day", {})))
    print(context_line(transcript_path))


if __name__ == "__main__":
    main()
