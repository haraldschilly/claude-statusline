#!/usr/bin/env python3
"""
Custom statusline for Claude Code
Shows: [git info] | [PR info] | [context usage] | [model@usage limits]

Repository: https://github.com/haraldschilly/claude-statusline
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


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


def get_git_info(cwd):
    """Get git repository information."""
    # Check if we're in a git repo
    if not run_cmd("git rev-parse --git-dir", cwd=cwd):
        return None

    # Get remote name (default to 'origin' or first remote)
    remote = run_cmd("git remote", cwd=cwd)
    if remote:
        remote = remote.split('\n')[0]
    else:
        remote = "local"

    # Get current branch
    branch = run_cmd("git branch --show-current", cwd=cwd)
    if not branch:
        # Detached HEAD state
        branch = run_cmd("git rev-parse --short HEAD", cwd=cwd) or "detached"

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
    # ANSI color codes for backgrounds
    GREEN_BG = '\033[42m\033[30m'  # Green background, black text
    ORANGE_BG = '\033[48;5;208m\033[30m'  # Orange background, black text
    RED_BG = '\033[41m\033[30m'  # Red background, black text
    RESET = '\033[0m'

    status_parts = []
    if added:
        status_parts.append(f"{GREEN_BG}[A{added}]{RESET}")
    if modified:
        status_parts.append(f"{ORANGE_BG}[M{modified}]{RESET}")
    if deleted:
        status_parts.append(f"{RED_BG}[D{deleted}]{RESET}")

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

    # Combine everything
    parts = [f"{remote}/{branch}"]
    if status_str:
        parts.append(status_str)
    if changes_str:
        parts.append(changes_str)

    return " ".join(parts)


def get_pr_info(cwd):
    """Get GitHub PR information using gh CLI."""
    # Check if gh is available
    if not run_cmd("command -v gh"):
        return None

    # Get current branch PR
    pr_info = run_cmd("gh pr view --json number,title 2>/dev/null", cwd=cwd)
    if not pr_info:
        return None

    try:
        pr_data = json.loads(pr_info)
        number = pr_data.get('number')
        title = pr_data.get('title', '')

        # Truncate title if too long
        if len(title) > 40:
            title = title[:37] + "..."

        return f"PR#{number}: {title}"
    except (json.JSONDecodeError, KeyError):
        return None


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


def get_usage_stats():
    """Get daily and weekly message counts as percentages of typical usage."""
    try:
        stats_file = Path.home() / '.claude' / 'stats-cache.json'
        if not stats_file.exists():
            return None, None

        with open(stats_file, 'r') as f:
            stats = json.load(f)

        daily_activity = stats.get('dailyActivity', [])
        if not daily_activity:
            return None, None

        # Get today's date and calculate week start
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())

        # Find today's activity
        today_str = today.strftime("%Y-%m-%d")
        today_msgs = 0
        week_msgs = 0

        for activity in daily_activity:
            activity_date = activity.get('date', '')
            msg_count = activity.get('messageCount', 0)

            if activity_date == today_str:
                today_msgs = msg_count

            # Count weekly messages
            try:
                act_date = datetime.strptime(activity_date, "%Y-%m-%d").date()
                if act_date >= week_start:
                    week_msgs += msg_count
            except ValueError:
                pass

        # Calculate percentages (assume 2000 daily, 10000 weekly as limits)
        # These are rough estimates - adjust based on your actual usage patterns
        daily_limit = 2000
        weekly_limit = 10000

        daily_pct = min(100, (today_msgs / daily_limit) * 100) if daily_limit > 0 else 0
        weekly_pct = min(100, (week_msgs / weekly_limit) * 100) if weekly_limit > 0 else 0

        return daily_pct, weekly_pct
    except (json.JSONDecodeError, KeyError, IOError):
        return None, None


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
    context_used = data.get('context_window', {}).get('used_percentage', 0)

    # Build statusline components
    components = []

    # Git information
    git_info = get_git_info(cwd)
    if git_info:
        components.append(git_info)

    # PR information
    pr_info = get_pr_info(cwd)
    if pr_info:
        components.append(pr_info)

    # Context usage with progress bar
    ctx_bar = progress_bar(context_used, width=8)
    components.append(f"ctx:{ctx_bar}")

    # Model and usage stats with progress bars
    daily_usage, weekly_usage = get_usage_stats()
    model_part = model_name

    if daily_usage is not None and weekly_usage is not None:
        daily_bar = progress_bar(daily_usage, width=8)
        weekly_bar = progress_bar(weekly_usage, width=8)
        model_part += f"@{daily_bar}/{weekly_bar}"
    elif daily_usage is not None:
        daily_bar = progress_bar(daily_usage, width=8)
        model_part += f"@{daily_bar}"

    components.append(model_part)

    # Output statusline
    statusline = " | ".join(components)
    print(statusline)


if __name__ == "__main__":
    main()
