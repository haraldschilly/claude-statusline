#!/usr/bin/env python3
"""
Custom statusline for Claude Code
Shows: [dir] | [git info] | [PR info] | [🧠 context] | [🔋 5h/7d limits] | [🤖 model]

Features:
- Real subscription rate-limit usage (5h + 7d) from Claude Code's stdin JSON
- Reset countdowns for both windows
- Colored progress bars and git status badges
- Cached PR lookup via `gh`

Repository: https://github.com/haraldschilly/claude-statusline
Inspired by: https://github.com/leeguooooo/claude-code-usage-bar
"""

import json
import re
import shutil
import subprocess
import sys
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')

# How long a cached `gh pr view` result stays valid (seconds).
PR_CACHE_TTL = 60


def visible_len(s: str) -> int:
    """Approximate display width: strip ANSI, count wide chars (emoji) as 2."""
    stripped = ANSI_RE.sub('', s)
    width = 0
    for ch in stripped:
        cp = ord(ch)
        if cp >= 0x1100 and (
            cp <= 0x115F
            or 0x2E80 <= cp <= 0x303E
            or 0x3041 <= cp <= 0xA4CF
            or 0xAC00 <= cp <= 0xD7A3
            or 0xF900 <= cp <= 0xFAFF
            or 0xFE30 <= cp <= 0xFE4F
            or 0xFF00 <= cp <= 0xFF60
            or 0xFFE0 <= cp <= 0xFFE6
            or 0x1F300 <= cp <= 0x1FAFF
            or 0x2600 <= cp <= 0x27BF
        ):
            width += 2
        else:
            width += 1
    return width


def truncate(s: str, max_len: int) -> str:
    """Truncate plain string (no ANSI) to max display width, appending …."""
    if len(s) <= max_len:
        return s
    return s[:max(1, max_len - 1)] + '…'


def run_cmd(args: List[str], cwd=None, timeout=2) -> Optional[str]:
    """Run a command (argument list, no shell) and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def collect_git_data(cwd) -> Optional[Dict[str, Any]]:
    """Gather git repository state once per render.

    Uses `git status --porcelain=v2 --branch`, which reports branch, upstream
    and file states in a single call.
    """
    toplevel = run_cmd(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    if not toplevel:
        return None

    status_output = run_cmd(["git", "status", "--porcelain=v2", "--branch"], cwd=cwd)
    if status_output is None:
        return None

    branch = upstream = oid = None
    modified = added = deleted = 0
    for line in status_output.split('\n'):
        if not line:
            continue
        if line.startswith('# branch.head '):
            branch = line[len('# branch.head '):]
        elif line.startswith('# branch.upstream '):
            upstream = line[len('# branch.upstream '):]
        elif line.startswith('# branch.oid '):
            oid = line[len('# branch.oid '):]
        elif line.startswith('? '):
            # Untracked files are new files, just not staged yet
            added += 1
        elif line[:2] in ('1 ', '2 ', 'u '):
            xy = line[2:4]
            if 'M' in xy or line[0] in ('2', 'u'):  # renamed/copied or unmerged
                modified += 1
            if 'A' in xy:
                added += 1
            if 'D' in xy:
                deleted += 1

    detached = branch in (None, '(detached)')
    if detached:
        branch = oid[:7] if oid and oid != '(initial)' else 'detached'

    # Remote tracked by the current branch
    remote = None
    if not detached:
        remote = run_cmd(["git", "config", f"branch.{branch}.remote"], cwd=cwd)
    if not remote and upstream:
        remote = upstream.split('/', 1)[0]
    if not remote:
        # Fallback: use 'origin' if it exists, else first remote, else 'local'
        remotes = run_cmd(["git", "remote"], cwd=cwd)
        if remotes:
            remote_list = remotes.split('\n')
            remote = "origin" if "origin" in remote_list else remote_list[0]
        else:
            remote = "local"

    # Line changes (staged + unstaged); --cached covers repos without a HEAD yet
    diff_stats = run_cmd(["git", "diff", "--numstat", "HEAD"], cwd=cwd)
    if diff_stats is None:
        diff_stats = run_cmd(["git", "diff", "--numstat", "--cached"], cwd=cwd)

    total_added = total_removed = 0
    if diff_stats:
        for line in diff_stats.split('\n'):
            parts = line.split('\t')
            if len(parts) >= 2:
                try:
                    total_added += int(parts[0]) if parts[0] != '-' else 0
                    total_removed += int(parts[1]) if parts[1] != '-' else 0
                except ValueError:
                    pass

    return {
        'toplevel': toplevel,
        'branch': branch,
        'detached': detached,
        'remote': remote,
        'added': added,
        'modified': modified,
        'deleted': deleted,
        'lines_added': total_added,
        'lines_removed': total_removed,
    }


def format_git(git: Optional[Dict[str, Any]], max_branch_len=60) -> Optional[str]:
    """Format collected git data into the display string."""
    if not git:
        return None

    # ANSI color codes for backgrounds with bold white text
    GREEN_BG = '\033[42m\033[1;97m'  # Green background, bold white text
    ORANGE_BG = '\033[48;5;208m\033[1;97m'  # Orange background, bold white text
    RED_BG = '\033[41m\033[1;97m'  # Red background, bold white text
    BOLD_GREEN = '\033[1;32m'
    BOLD_RED = '\033[1;31m'
    RESET = '\033[0m'

    parts = [f"{git['remote']}/{truncate(git['branch'], max_branch_len)}"]

    badges = []
    if git['added']:
        badges.append(f"{GREEN_BG}A{git['added']}{RESET}")
    if git['modified']:
        badges.append(f"{ORANGE_BG}M{git['modified']}{RESET}")
    if git['deleted']:
        badges.append(f"{RED_BG}D{git['deleted']}{RESET}")
    if badges:
        parts.append(" ".join(badges))

    changes = []
    if git['lines_added']:
        changes.append(f"{BOLD_GREEN}+{git['lines_added']}{RESET}")
    if git['lines_removed']:
        changes.append(f"{BOLD_RED}-{git['lines_removed']}{RESET}")
    if changes:
        parts.append(" ".join(changes))

    return " ".join(parts)


def pr_cache_path() -> Path:
    base = os.environ.get('XDG_CACHE_HOME') or str(Path.home() / '.cache')
    return Path(base) / 'claude-statusline' / 'pr-cache.json'


def fetch_pr_data(git: Optional[Dict[str, Any]]):
    """Return (number, title) of the current branch's PR, or None.

    `gh pr view` is a network call, so results (including "no PR") are cached
    per repo+branch for PR_CACHE_TTL seconds.
    """
    if not git or git['detached']:
        return None

    key = f"{git['toplevel']}\0{git['branch']}"
    cache_file = pr_cache_path()
    try:
        cache = json.loads(cache_file.read_text())
        if not isinstance(cache, dict):
            cache = {}
    except (OSError, ValueError):
        cache = {}

    now = time.time()
    entry = cache.get(key)
    if isinstance(entry, dict) and now - entry.get('ts', 0) < PR_CACHE_TTL:
        pr = entry.get('pr')
        return tuple(pr) if pr else None

    pr = None
    if shutil.which('gh'):
        pr_info = run_cmd(["gh", "pr", "view", "--json", "number,title"], cwd=git['toplevel'])
        if pr_info:
            try:
                pr_data = json.loads(pr_info)
                pr = (pr_data.get('number'), pr_data.get('title', ''))
            except (json.JSONDecodeError, AttributeError):
                pr = None

    # Store result, dropping expired entries; write atomically (parallel sessions)
    cache = {k: v for k, v in cache.items()
             if isinstance(v, dict) and now - v.get('ts', 0) < PR_CACHE_TTL}
    cache[key] = {'ts': now, 'pr': list(pr) if pr else None}
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_file.with_suffix(f'.{os.getpid()}.tmp')
        tmp.write_text(json.dumps(cache))
        os.replace(tmp, cache_file)
    except OSError:
        pass

    return pr


def format_pr(pr_data, max_title_len=40):
    """Format cached PR data into display string."""
    if not pr_data:
        return None
    number, title = pr_data
    return f"PR#{number}: {truncate(title, max_title_len)}"


def bar_color(percentage):
    """ANSI color for a usage level: green <80%, orange 80-89%, red >=90%."""
    if percentage >= 90:
        return '\033[91m'
    if percentage >= 80:
        return '\033[38;5;208m'
    return '\033[32m'


def progress_bar(percentage, width=8):
    """
    Create an ASCII progress bar with color coding.

    Args:
        percentage: Value from 0-100
        width: Width of the progress bar in characters (default 8)

    Returns:
        Colored ASCII progress bar string
    """
    RESET = '\033[0m'
    color = bar_color(percentage)

    # Calculate filled and empty portions.
    # Clamp to [0, width] so a percentage >100% (over budget) renders a full
    # bar instead of overflowing and breaking the statusline layout.
    filled = max(0, min(width, int((percentage / 100) * width)))
    empty = width - filled

    # Use Unicode block characters for smooth progress
    bar = '█' * filled + '░' * empty

    return f"{color}{bar}{RESET}"


def format_duration(seconds: float) -> str:
    """Format a countdown: 1h05m below a day, 3d04h above."""
    total_minutes = max(0, int(seconds // 60))
    hours, mins = divmod(total_minutes, 60)
    if hours >= 24:
        days, hours = divmod(hours, 24)
        return f"{days}d{hours:02d}h"
    return f"{hours}h{mins:02d}m"


def active_window(window: Any):
    """Return (used_percentage, seconds_until_reset) of a rate-limit window.

    None if the window is absent or has already reset.
    """
    if not isinstance(window, dict) or window.get('used_percentage') is None:
        return None
    pct = window['used_percentage']
    resets_at = window.get('resets_at')
    remaining = resets_at - time.time() if resets_at is not None else None
    if remaining is not None and remaining <= 0:
        return None
    return pct, remaining


def format_rate_limits(rate_limits: Dict[str, Any], width=8) -> Optional[str]:
    """Render the 5h and 7d rate limits as one double-row bar.

    Top half = 5h window, bottom half = 7d window: '█' where both are
    filled, then '▀' or '▄' for whichever window reaches further, then blanks.
    The whole bar has one color, taken from the higher of the two values.
    Percentages are only spelled out (in red) from 90% on; the 5h reset
    countdown is always shown.
    """
    five = active_window(rate_limits.get('five_hour'))
    week = active_window(rate_limits.get('seven_day'))
    if not five and not week:
        return None

    RED, RESET = '\033[91m', '\033[0m'

    def filled(win):
        if not win:
            return 0
        return max(0, min(width, round(win[0] / 100 * width)))

    top_n, bot_n = filled(five), filled(week)
    cells = ''.join(
        '█' if i < top_n and i < bot_n else
        '▀' if i < top_n else
        '▄' if i < bot_n else
        ' '
        for i in range(width)
    )
    peak = max(win[0] for win in (five, week) if win)
    bar = f"{bar_color(peak)}{cells}{RESET}"

    text = f"🔋{bar}"
    if five and five[1] is not None:
        text += f" {format_duration(five[1])}"
    if five and five[0] >= 90:
        text += f" {RED}5h {five[0]:.0f}%{RESET}"
    if week and week[0] >= 90:
        text += f" {RED}7d {week[0]:.0f}%"
        if week[1] is not None:
            text += f" {format_duration(week[1])}"
        text += RESET
    return text


def get_effort_level(data: Dict[str, Any]) -> Optional[str]:
    """Current effort level: stdin JSON, then env var, then settings file."""
    effort = (data.get('effort') or {}).get('level')
    if effort:
        return effort
    effort = os.environ.get("CLAUDE_CODE_EFFORT_LEVEL")
    if effort:
        return effort
    settings_candidates = []
    env_cfg = os.environ.get("CLAUDE_CONFIG_DIR")
    if env_cfg:
        settings_candidates.append(Path(env_cfg).expanduser() / 'settings.json')
    settings_candidates += [
        Path.home() / '.claude' / 'settings.json',
        Path.home() / '.config' / 'claude' / 'settings.json',
    ]
    for settings_path in settings_candidates:
        try:
            with open(settings_path) as f:
                effort = json.load(f).get('effortLevel')
            if effort:
                return effort
        except Exception:
            pass
    return None


def main():
    """Main statusline function."""
    try:
        # Read JSON data from stdin
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("Error: Invalid JSON input")
        return

    # Extract information from JSON
    cwd = (data.get('workspace') or {}).get('current_dir') or str(Path.cwd())
    model_name = (data.get('model') or {}).get('display_name', 'Unknown')
    # Shorten verbose context suffix like "(1M context)" to "[1M]"
    model_name = re.sub(r'\s*\(([0-9]+[kKmM])\s+context\)', r' [\1]', model_name)
    # used_percentage may be null early in a session
    context_used = (data.get('context_window') or {}).get('used_percentage') or 0

    # Terminal width for adaptive truncation (fallback 120)
    try:
        term_width = int(os.environ.get('COLUMNS') or 0) or shutil.get_terminal_size(fallback=(120, 24)).columns
    except Exception:
        term_width = 120

    # Gather everything once; the truncation loop below only re-formats.
    git = collect_git_data(cwd)
    dir_name = Path(git['toplevel']).name if git else Path(cwd).name
    pr_data = fetch_pr_data(git)

    ctx_text = f"🧠 {progress_bar(context_used, width=8)}"

    # Subscription rate limits (Pro/Max only, present after the first API response)
    rate_limits = data.get('rate_limits') or {}
    limits_text = format_rate_limits(rate_limits)

    effort_icons = {
        'low': '▁',
        'medium': '▃',
        'high': '▅',
        'xhigh': '▇',
    }
    effort_name = get_effort_level(data) or 'medium'
    effort_icon = effort_icons.get(effort_name, '❔')
    model_text = f"🤖 {model_name} {effort_icon} {effort_name}"

    def render(branch_len, pr_len):
        parts = [dir_name]
        g = format_git(git, max_branch_len=branch_len)
        if g:
            parts.append(g)
        p = format_pr(pr_data, max_title_len=pr_len)
        if p:
            parts.append(p)
        parts.append(ctx_text)
        if limits_text:
            parts.append(limits_text)
        parts.append(model_text)
        return " | ".join(parts)

    # Adaptive truncation: iteratively shrink branch and PR title to fit.
    branch_budget = 60
    pr_title_budget = 80
    statusline = render(branch_budget, pr_title_budget)
    while visible_len(statusline) > term_width and (branch_budget > 10 or pr_title_budget > 12):
        branch_budget = max(10, branch_budget - 4)
        pr_title_budget = max(12, pr_title_budget - 4)
        statusline = render(branch_budget, pr_title_budget)

    print(statusline)


if __name__ == "__main__":
    main()
