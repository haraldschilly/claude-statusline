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
import subprocess
import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List


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

    # Model name at the end
    components.append(f"🤖 {model_name}")

    # Output statusline
    statusline = " | ".join(components)
    print(statusline)


if __name__ == "__main__":
    main()
