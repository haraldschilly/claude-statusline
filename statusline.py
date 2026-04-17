#!/usr/bin/env python3
"""
Custom statusline for Claude Code
Shows: [git info] | [PR info] | [🧠 context] | [🔋 tokens] | [⏱️ timer] | [🤖 model]

Features:
- Real token usage tracking from .jsonl files
- Adaptive P90 limits from usage history
- 5-hour session countdown timer
- Colored progress bars and git status badges

Repository: https://github.com/haraldschilly/claude-statusline
Inspired by: https://github.com/leeguooooo/claude-code-usage-bar
"""

import json
import re
import shutil
import subprocess
import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')


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


def run_cmd(cmd, cwd=None, check=False):
    """Run a shell command and return output, or None on error."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=2
        )
        if check and result.returncode != 0:
            return None
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return None


def get_git_info(cwd, max_branch_len=60):
    """Get git repository information."""
    # Check if we're in a git repo
    if not run_cmd("git rev-parse --git-dir", cwd=cwd):
        return None

    # Get current branch (raw name, used to look up tracking remote)
    branch_raw = run_cmd("git branch --show-current", cwd=cwd)
    if not branch_raw:
        # Detached HEAD state
        branch_raw = run_cmd("git rev-parse --short HEAD", cwd=cwd) or "detached"

    # Get the remote that the current branch is tracking (use untruncated name)
    remote = run_cmd(f"git config branch.{branch_raw}.remote", cwd=cwd) if branch_raw else None
    if not remote:
        # Fallback: use 'origin' if it exists, else first remote, else 'local'
        remotes = run_cmd("git remote", cwd=cwd)
        if remotes:
            remote_list = remotes.split('\n')
            remote = "origin" if "origin" in remote_list else remote_list[0]
        else:
            remote = "local"

    # Get status information
    status_output = run_cmd("git status --porcelain", cwd=cwd) or ""

    # Count M/D/A files
    modified = added = deleted = 0
    for line in status_output.split('\n'):
        if not line:
            continue
        status = line[:2]
        if 'M' in status:
            modified += 1
        if 'A' in status:
            added += 1
        if 'D' in status:
            deleted += 1

    # Get line changes (staged + unstaged)
    diff_stats = run_cmd("git diff --numstat HEAD 2>/dev/null || git diff --numstat --cached", cwd=cwd)

    total_added = total_removed = 0
    if diff_stats:
        for line in diff_stats.split('\n'):
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) >= 2:
                try:
                    total_added += int(parts[0]) if parts[0] != '-' else 0
                    total_removed += int(parts[1]) if parts[1] != '-' else 0
                except ValueError:
                    pass

    # Build status string with colored badges
    # ANSI color codes for backgrounds with bold white text
    GREEN_BG = '\033[42m\033[1;97m'  # Green background, bold white text
    ORANGE_BG = '\033[48;5;208m\033[1;97m'  # Orange background, bold white text
    RED_BG = '\033[41m\033[1;97m'  # Red background, bold white text
    RESET = '\033[0m'

    status_parts = []
    if added:
        status_parts.append(f"{GREEN_BG}A{added}{RESET}")
    if modified:
        status_parts.append(f"{ORANGE_BG}M{modified}{RESET}")
    if deleted:
        status_parts.append(f"{RED_BG}D{deleted}{RESET}")

    status_str = " ".join(status_parts) if status_parts else ""

    # Add line changes with bold colors
    BOLD_GREEN = '\033[1;32m'  # Bold green
    BOLD_RED = '\033[1;31m'  # Bold red
    RESET_LINE = '\033[0m'

    changes = []
    if total_added:
        changes.append(f"{BOLD_GREEN}+{total_added}{RESET_LINE}")
    if total_removed:
        changes.append(f"{BOLD_RED}-{total_removed}{RESET_LINE}")
    changes_str = " ".join(changes)

    # Truncate branch name only for display (not for git lookups above)
    branch = truncate(branch_raw, max_branch_len)

    # Combine everything
    parts = [f"{remote}/{branch}"]
    if status_str:
        parts.append(status_str)
    if changes_str:
        parts.append(changes_str)

    return " ".join(parts)


def fetch_pr_data(cwd):
    """Fetch raw PR data once (number and title). Returns (number, title) or None."""
    if not run_cmd("command -v gh"):
        return None
    pr_info = run_cmd("gh pr view --json number,title 2>/dev/null", cwd=cwd)
    if not pr_info:
        return None
    try:
        pr_data = json.loads(pr_info)
        return pr_data.get('number'), pr_data.get('title', '')
    except (json.JSONDecodeError, KeyError):
        return None


def format_pr(pr_data, max_title_len=40):
    """Format cached PR data into display string."""
    if not pr_data:
        return None
    number, title = pr_data
    return f"PR#{number}: {truncate(title, max_title_len)}"


def progress_bar(percentage, width=8):
    """
    Create an ASCII progress bar with color coding.

    Args:
        percentage: Value from 0-100
        width: Width of the progress bar in characters (default 8)

    Returns:
        Colored ASCII progress bar string
    """
    # ANSI color codes
    RESET = '\033[0m'
    GREEN = '\033[32m'
    ORANGE = '\033[38;5;208m'
    RED = '\033[91m'

    # Choose color based on percentage
    if percentage >= 90:
        color = RED
    elif percentage >= 80:
        color = ORANGE
    else:
        color = GREEN

    # Calculate filled and empty portions
    filled = int((percentage / 100) * width)
    empty = width - filled

    # Use Unicode block characters for smooth progress
    bar = '█' * filled + '░' * empty

    return f"{color}{bar}{RESET}"


def get_claude_data_path() -> Optional[Path]:
    """Find Claude data directory."""
    # Check env override
    env_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    if env_dir:
        env_path = Path(env_dir).expanduser()
        if env_path.name == ".claude":
            if (env_path / "projects").exists():
                return env_path / "projects"
            return env_path
        else:
            if (env_path / ".claude" / "projects").exists():
                return env_path / ".claude" / "projects"
            return env_path / ".claude"

    # Check standard locations
    candidates = [
        Path.home() / '.claude' / 'projects',
        Path.home() / '.config' / 'claude' / 'projects',
        Path.home() / '.claude',
    ]

    for path in candidates:
        if path.exists() and path.is_dir():
            return path

    return None


def analyze_usage_data() -> Optional[Dict[str, Any]]:
    """Analyze Claude usage data from .jsonl files.

    A "session" starts at the first message and lasts 5 hours from that
    timestamp. The next message ≥5h after the session start begins a new
    session. Entries are gathered from all jsonl files, sorted by timestamp,
    and grouped accordingly.
    """
    try:
        data_path = get_claude_data_path()
        if not data_path:
            return None

        now_utc = datetime.now(timezone.utc)
        history_cutoff = now_utc - timedelta(days=8)

        # Collect every usage entry (timestamp, tokens, cost) from the last 8 days.
        entries = []
        for jsonl_file in data_path.rglob("*.jsonl"):
            try:
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)

                            timestamp_str = data.get('timestamp', '')
                            if not timestamp_str:
                                continue
                            if timestamp_str.endswith('Z'):
                                timestamp_str = timestamp_str[:-1] + '+00:00'
                            timestamp = datetime.fromisoformat(timestamp_str)

                            if timestamp < history_cutoff:
                                continue

                            usage = data.get('usage', {})
                            if not usage and 'message' in data and isinstance(data['message'], dict):
                                usage = data['message'].get('usage', {})
                            if not usage:
                                continue

                            input_tokens = usage.get('input_tokens', 0)
                            output_tokens = usage.get('output_tokens', 0)
                            cache_creation = usage.get('cache_creation_input_tokens', 0)
                            total = input_tokens + output_tokens + cache_creation
                            if total == 0:
                                continue

                            # Estimate cost (Sonnet 3.5 pricing: input $3/M, output $15/M)
                            cost = (input_tokens * 3 + output_tokens * 15 + cache_creation * 3.75) / 1000000

                            entries.append((timestamp, total, cost))
                        except (json.JSONDecodeError, ValueError, TypeError):
                            continue
            except Exception:
                continue

        if not entries:
            return None

        entries.sort(key=lambda e: e[0])

        # Group into sessions: session_start + 5h defines the session window.
        # The next entry ≥5h after session_start begins a new session.
        sessions = []
        cur_start = None
        cur_tokens = 0
        cur_cost = 0.0
        for ts, tokens, cost in entries:
            if cur_start is None or (ts - cur_start).total_seconds() >= 5 * 3600:
                if cur_start is not None:
                    sessions.append({'start': cur_start, 'tokens': cur_tokens, 'cost': cur_cost})
                cur_start = ts
                cur_tokens = 0
                cur_cost = 0.0
            cur_tokens += tokens
            cur_cost += cost
        if cur_start is not None:
            sessions.append({'start': cur_start, 'tokens': cur_tokens, 'cost': cur_cost})

        # Determine the active session: the most recent one, only if still
        # within its 5h window from now.
        active = sessions[-1] if sessions else None
        if not active or (now_utc - active['start']).total_seconds() >= 5 * 3600:
            return None

        total_tokens = active['tokens']
        total_cost = active['cost']
        session_start = active['start']

        # Historical sessions (excluding the active one) feed P90 limits.
        historical = sessions[:-1] if len(sessions) > 1 else []

        if len(historical) >= 5:
            session_tokens = sorted(s['tokens'] for s in historical)
            session_costs = sorted(s['cost'] for s in historical)
            p90_index = int(len(session_tokens) * 0.9)
            token_limit = max(session_tokens[min(p90_index, len(session_tokens) - 1)], 19000)
            cost_limit = max(session_costs[min(p90_index, len(session_costs) - 1)] * 1.2, 18.0)
        else:
            if total_tokens > 100000:
                token_limit, cost_limit = 220000, 140.0
            elif total_tokens > 50000:
                token_limit, cost_limit = 88000, 35.0
            else:
                token_limit, cost_limit = 19000, 18.0

        return {
            'total_tokens': total_tokens,
            'token_limit': int(token_limit),
            'cost_usd': total_cost,
            'cost_limit': cost_limit,
            'session_start': session_start,
        }

    except Exception:
        return None


def calculate_reset_time(session_start: Optional[datetime] = None) -> str:
    """Calculate time until session reset (5-hour rolling window)."""
    try:
        if session_start:
            session_end = session_start + timedelta(hours=5)
            now = datetime.now(timezone.utc)

            if session_end > now:
                diff = session_end - now
                total_minutes = int(diff.total_seconds() / 60)
                hours = total_minutes // 60
                mins = total_minutes % 60
                return f"{hours}h{mins:02d}m"

        # Fallback: estimate next reset
        now = datetime.now()
        today_2pm = now.replace(hour=14, minute=0, second=0, microsecond=0)
        next_reset = today_2pm if now < today_2pm else today_2pm + timedelta(days=1)
        diff = next_reset - now

        total_minutes = int(diff.total_seconds() / 60)
        hours = total_minutes // 60
        mins = total_minutes % 60

        return f"{hours}h{mins:02d}m"
    except Exception:
        return "N/A"


def format_number(num: float) -> str:
    """Format number for display (e.g., 48000 -> 48.0k)."""
    if num >= 1000000:
        return f"{num/1000000:.1f}M"
    elif num >= 1000:
        return f"{num/1000:.1f}k"
    else:
        return f"{num:.0f}"


def main():
    """Main statusline function."""
    try:
        # Read JSON data from stdin
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("Error: Invalid JSON input")
        return

    # Extract information from JSON
    cwd = data.get('workspace', {}).get('current_dir', str(Path.cwd()))
    model_name = data.get('model', {}).get('display_name', 'Unknown')
    # Shorten verbose context suffix like "(1M context)" to "[1M]"
    model_name = re.sub(r'\s*\(([0-9]+[kKmM])\s+context\)', r' [\1]', model_name)
    context_used = data.get('context_window', {}).get('used_percentage', 0)

    # Terminal width for adaptive truncation (fallback 120)
    try:
        term_width = int(os.environ.get('COLUMNS') or 0) or shutil.get_terminal_size(fallback=(120, 24)).columns
    except Exception:
        term_width = 120

    # Generous initial budgets; actual truncation happens after measuring below.
    branch_budget = 60
    pr_title_budget = 80

    # Build statusline components
    components = []

    # Directory name (git root basename, or cwd basename as fallback)
    git_toplevel = run_cmd("git rev-parse --show-toplevel", cwd=cwd)
    dir_name = Path(git_toplevel).name if git_toplevel else Path(cwd).name
    components.append(dir_name)

    # Git information
    git_info = get_git_info(cwd, max_branch_len=branch_budget)
    if git_info:
        components.append(git_info)

    # PR information (fetch once, reformat as needed)
    pr_data = fetch_pr_data(cwd)
    pr_info = format_pr(pr_data, max_title_len=pr_title_budget)
    if pr_info:
        components.append(pr_info)

    # Context usage with progress bar
    ctx_bar = progress_bar(context_used, width=8)
    components.append(f"🧠 {ctx_bar}")

    # Analyze usage data from Claude files
    usage_data = analyze_usage_data()

    if usage_data:
        # Token usage with progress bar
        token_pct = (usage_data['total_tokens'] / usage_data['token_limit']) * 100 if usage_data['token_limit'] > 0 else 0
        token_bar = progress_bar(token_pct, width=8)
        tokens_text = f"🔋{format_number(usage_data['total_tokens'])}/{format_number(usage_data['token_limit'])} {token_bar}"

        # # Cost with progress bar
        # cost_pct = (usage_data['cost_usd'] / usage_data['cost_limit']) * 100 if usage_data['cost_limit'] > 0 else 0
        # cost_bar = progress_bar(cost_pct, width=8)
        # cost_text = f"💰${usage_data['cost_usd']:.2f}/${usage_data['cost_limit']:.2f} {cost_bar}"

        # Reset countdown timer
        reset_time = calculate_reset_time(usage_data.get('session_start'))
        time_text = f"⏱️ {reset_time}"

        components.extend([tokens_text, time_text])

    # Effort level (env var overrides settings file)
    effort = os.environ.get("CLAUDE_CODE_EFFORT_LEVEL")
    if not effort:
        for settings_path in [
            Path.home() / '.claude' / 'settings.json',
            Path.home() / '.config' / 'claude' / 'settings.json',
        ]:
            if settings_path.exists():
                try:
                    with open(settings_path) as f:
                        effort = json.load(f).get('effortLevel')
                    if effort:
                        break
                except Exception:
                    pass
    effort_icons = {
        'low': '▁',
        'medium': '▃',
        'high': '▅',
        'xhigh': '▇',
    }
    effort_name = effort or 'medium'
    effort_icon = effort_icons.get(effort_name, '❔')
    effort_text = f"{effort_icon} {effort_name}"

    # Model name and effort at the end
    components.append(f"🤖 {model_name} {effort_text}")

    # Adaptive truncation: iteratively shrink branch and PR title to fit.
    def render(branch_len, pr_len):
        parts = [dir_name]
        g = get_git_info(cwd, max_branch_len=branch_len)
        if g:
            parts.append(g)
        p = format_pr(pr_data, max_title_len=pr_len)
        if p:
            parts.append(p)
        parts.append(f"🧠 {ctx_bar}")
        if usage_data:
            parts.extend([tokens_text, time_text])
        parts.append(f"🤖 {model_name} {effort_text}")
        return " | ".join(parts)

    statusline = " | ".join(components)
    while visible_len(statusline) > term_width and (branch_budget > 10 or pr_title_budget > 12):
        branch_budget = max(10, branch_budget - 4)
        pr_title_budget = max(12, pr_title_budget - 4)
        statusline = render(branch_budget, pr_title_budget)

    print(statusline)


if __name__ == "__main__":
    main()
