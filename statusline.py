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
    """Analyze Claude usage data from .jsonl files."""
    try:
        data_path = get_claude_data_path()
        if not data_path:
            return None

        # Collect data from the last 5 hours (current session window)
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=5)
        current_session_data = []

        # Collect historical data for P90 calculation (last 8 days)
        history_cutoff = datetime.now(timezone.utc) - timedelta(days=8)
        all_sessions = []
        current_session_tokens = 0
        current_session_cost = 0.0
        last_time = None

        # Read all JSONL files
        for jsonl_file in sorted(data_path.rglob("*.jsonl"), key=lambda f: f.stat().st_mtime):
            try:
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            data = json.loads(line)

                            # Parse timestamp
                            timestamp_str = data.get('timestamp', '')
                            if not timestamp_str:
                                continue

                            if timestamp_str.endswith('Z'):
                                timestamp_str = timestamp_str[:-1] + '+00:00'

                            timestamp = datetime.fromisoformat(timestamp_str)

                            # Extract usage data
                            usage = data.get('usage', {})
                            if not usage and 'message' in data and isinstance(data['message'], dict):
                                usage = data['message'].get('usage', {})

                            if not usage:
                                continue

                            # Calculate tokens
                            input_tokens = usage.get('input_tokens', 0)
                            output_tokens = usage.get('output_tokens', 0)
                            cache_creation = usage.get('cache_creation_input_tokens', 0)

                            total_tokens = input_tokens + output_tokens + cache_creation

                            if total_tokens == 0:
                                continue

                            # Estimate cost (Sonnet 3.5 pricing: input $3/M, output $15/M)
                            cost = (input_tokens * 3 + output_tokens * 15 + cache_creation * 3.75) / 1000000

                            entry = {
                                'timestamp': timestamp,
                                'total_tokens': total_tokens,
                                'cost': cost,
                            }

                            # Current 5-hour session data
                            if timestamp >= cutoff_time:
                                current_session_data.append(entry)

                            # Historical session grouping (for P90 calculation)
                            if timestamp >= history_cutoff:
                                if (last_time is None or
                                    (timestamp - last_time).total_seconds() > 5 * 3600):
                                    # Save previous session
                                    if current_session_tokens > 0:
                                        all_sessions.append({
                                            'tokens': current_session_tokens,
                                            'cost': current_session_cost
                                        })
                                    # Start new session
                                    current_session_tokens = total_tokens
                                    current_session_cost = cost
                                else:
                                    # Continue current session
                                    current_session_tokens += total_tokens
                                    current_session_cost += cost

                                last_time = timestamp

                        except (json.JSONDecodeError, ValueError, TypeError):
                            continue

            except Exception:
                continue

        # Save last session
        if current_session_tokens > 0:
            all_sessions.append({
                'tokens': current_session_tokens,
                'cost': current_session_cost
            })

        if not current_session_data:
            return None

        # Calculate current session statistics
        total_tokens = sum(e['total_tokens'] for e in current_session_data)
        total_cost = sum(e['cost'] for e in current_session_data)

        # Calculate P90 limit from historical sessions
        if len(all_sessions) >= 5:
            session_tokens = [s['tokens'] for s in all_sessions]
            session_costs = [s['cost'] for s in all_sessions]
            session_tokens.sort()
            session_costs.sort()

            p90_index = int(len(session_tokens) * 0.9)
            token_limit = max(session_tokens[min(p90_index, len(session_tokens) - 1)], 19000)
            cost_limit = max(session_costs[min(p90_index, len(session_costs) - 1)] * 1.2, 18.0)
        else:
            # Default limits based on current usage
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
            'messages_count': len(current_session_data),
            'session_start': current_session_data[0]['timestamp'] if current_session_data else None,
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
