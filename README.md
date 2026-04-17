# Claude Code Statusline

A beautiful, informative statusline for [Claude Code](https://claude.com/code) with real token usage tracking, visual progress bars, git integration, and session countdown timer.

## Features

- 🔋 **Real Token Usage Tracking** - Analyzes actual token consumption from Claude's `.jsonl` files
- 📊 **Visual Progress Bars** - Color-coded ASCII bars that change from green → orange → red as limits approach
- ⏱️ **Session Countdown Timer** - Shows time remaining until your 5-hour session resets
- 📈 **Smart P90 Limits** - Automatically calculates personalized usage limits from your history (90th percentile)
- 🎨 **Colored File Badges** - File status with colored backgrounds: 🟢 A# 🟠 M# 🔴 D#
- 💚 **Bold Line Changes** - Line additions in bold green (+NN), deletions in bold red (-NN)
- 🎯 **Smart Color Coding** - Green (<80%), Orange (80-89%), Red (≥90%)
- 🔄 **Git Integration** - Shows branch, remote, file status badges, and line changes
- 🔀 **Pull Request Info** - Displays PR number and title (via `gh` CLI)
- ▃ **Effort Level Indicator** - Block bar showing current reasoning effort (▁ low, ▃ medium, ▅ high, ▇ xhigh)
- 📁 **Project Directory** - Shows git root directory name (or working directory) at a glance
- ⚡ **Fast & Lightweight** - Pure Python, no external dependencies

## Preview

```bash
# Normal usage (green progress bars, colored badges):
my-project | origin/main A3 M1 +45 -12 | 🧠███░░░░░ | 🔋843.4k/4.2M █░░░░░░░ | ⏱️ 0h46m | 🤖 Sonnet 4.5 ▃ medium
# A3 = green background, M1 = orange background
# +45 = bold green, -12 = bold red

# With Pull Request:
my-app | origin/feature M2 | PR#123: Add authentication | 🧠█████░░░ | 🔋1.2M/4.2M ███░░░░░ | ⏱️ 2h15m | 🤖 Opus ▅ high

# Warning level (orange bars at 80%+):
my-project | origin/hotfix A5 D1 +102 -87 | 🧠██████░░ | 🔋3.5M/4.2M ██████░░ | ⏱️ 1h30m | 🤖 Sonnet ▃ medium

# Critical level (red bars at 90%+):
my-project | origin/bugfix M3 D2 +23 -45 | 🧠███████░ | 🔋3.9M/4.2M ███████░ | ⏱️ 0h22m | 🤖 Sonnet 🌑 low
```

## Components

| Component | Description | Example |
|-----------|-------------|---------|
| **Directory** | Git root directory basename (or working directory) | `my-project` |
| **Git Info** | Remote/branch, colored file status badges, line changes | `origin/main A3 M1 +45 -12` |
| **PR Status** | Pull request number and title (requires `gh` CLI) | `PR#123: Add new feature` |
| **Context** | Current session context window usage with visual bar | `🧠 ███░░░░░` |
| **Token Usage** | Real token consumption with limit and progress bar | `🔋843.4k/4.2M █░░░░░░░` |
| **Reset Timer** | Countdown to 5-hour session reset | `⏱️ 0h46m` |
| **Model & Effort** | Current Claude model and reasoning effort level | `🤖 Sonnet 4.5 ▃ medium` |

### File Status Badge Colors

- 🟢 **A#** - Added files (green background)
- 🟠 **M#** - Modified files (orange background)
- 🔴 **D#** - Deleted files (red background)

### Effort Level Icons

- ▁ **low** - Minimal reasoning
- ▃ **medium** - Balanced (default)
- ▅ **high** - Deep reasoning
- ▇ **xhigh** - Maximum reasoning

The effort level is read from the `CLAUDE_CODE_EFFORT_LEVEL` environment variable first, then from `~/.claude/settings.json` (`effortLevel` key). Change it mid-session with `/effort low|medium|high|xhigh`.

### Token Tracking

The statusline analyzes your actual token usage from `~/.claude/projects/*.jsonl` files:

- **Tokens**: Input + Output + Cache creation tokens
- **Limits**: Calculated from your usage history (90th percentile) over the last 8 days
- **Session**: 5-hour rolling window that resets automatically

## Installation

### Quick Install

```bash
# Clone the repository
git clone https://github.com/haraldschilly/claude-statusline.git ~/.claude-statusline

# Run the install script
~/.claude-statusline/install.sh
```

### Manual Install

```bash
# 1. Clone the repository
git clone https://github.com/haraldschilly/claude-statusline.git ~/.claude-statusline

# 2. Make the script executable
chmod +x ~/.claude-statusline/statusline.py

# 3. Create symlink (recommended) or copy
ln -sf ~/.claude-statusline/statusline.py ~/.claude/statusline.py

# 4. Add to Claude Code settings
# Edit ~/.claude/settings.json and add:
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/statusline.py",
    "padding": 0
  }
}
```

### Requirements

- **Python 3** (required) - For the statusline script
- **git** (optional) - For git repository information
- **gh CLI** (optional) - For pull request information
  - Install: `sudo apt install gh` or visit [cli.github.com](https://cli.github.com/)

## Configuration

### Usage Limits

Limits are **automatically calculated** from your usage history using the 90th percentile (P90) method:

- Analyzes your last 8 days of sessions
- Calculates the 90th percentile of token usage
- Adapts to your actual usage patterns over time
- Falls back to sensible defaults if insufficient history

**Default fallback limits:**
- Light usage: 19k tokens
- Medium usage: 88k tokens
- Heavy usage: 220k tokens

### Customize Progress Bars

**Change bar width** (search for `width=8` in `main()`):
```python
token_bar = progress_bar(token_pct, width=10)  # Change from 8 to 10
```

**Adjust color thresholds** (in `progress_bar()` function):
```python
if percentage >= 90:      # Red threshold (default: 90%)
    color = RED
elif percentage >= 80:    # Orange threshold (default: 80%)
    color = ORANGE
else:
    color = GREEN
```

**Use different characters** (in `progress_bar()` function):
```python
bar = '█' * filled + '░' * empty  # Try: ▓/▒, ■/□, ●/○, ═/─, etc.
```

### PR Title Length

Change the truncation length (line 129):
```python
if len(title) > 40:  # Change 40 to your preferred length
    title = title[:37] + "..."
```

### Hide Components

Comment out sections in `main()` function to hide components:

```python
# Hide PR information:
# pr_info = get_pr_info(cwd)
# if pr_info:
#     components.append(pr_info)

# Hide git information:
# git_info = get_git_info(cwd)
# if git_info:
#     components.append(git_info)
```

## How It Works

Claude Code calls your statusline script periodically, passing context information via stdin as JSON:

```json
{
  "model": {"display_name": "Sonnet 4.5"},
  "workspace": {"current_dir": "/path/to/project"},
  "context_window": {"used_percentage": 42.5}
}
```

The script:
1. Extracts model, context, and workspace info from JSON
2. Queries git status from the current directory
3. Checks for GitHub PR info (if `gh` CLI is available)
4. **Analyzes actual token usage** from `~/.claude/projects/*.jsonl` files
   - Reads all conversation data from the last 5 hours (current session)
   - Extracts input/output/cache tokens from usage metadata
5. **Calculates personalized limits** using P90 method
   - Analyzes last 8 days of session history
   - Uses 90th percentile as adaptive threshold
6. **Calculates session reset time**
   - Finds session start from first entry timestamp
   - Adds 5 hours to determine reset time
   - Shows countdown in hours and minutes
7. Generates colored progress bars
8. Outputs the formatted statusline

### Data Sources

- **Context window**: From Claude Code's JSON input (stdin)
- **Git info**: From git commands in workspace directory
- **PR info**: From `gh` CLI (GitHub API)
- **Token usage**: From `~/.claude/projects/*.jsonl` files
- **Usage limits**: Calculated from historical `.jsonl` data (P90)

## Troubleshooting

### Statusline not appearing
- Restart Claude Code after modifying `settings.json`
- Verify the script is executable: `chmod +x ~/.claude/statusline.py`
- Test manually: `echo '{"context_window":{"used_percentage":50},"model":{"display_name":"Test"},"workspace":{"current_dir":"'$(pwd)'"}}' | ~/.claude/statusline.py`

### Git info not showing
- Ensure you're in a git repository: `git status`
- The script gracefully skips git info if not in a repo

### PR info not showing
- Install gh CLI: `sudo apt install gh` or visit [cli.github.com](https://cli.github.com/)
- Authenticate: `gh auth login`
- Ensure your branch has an associated PR: `gh pr view`

### Colors not working
- Ensure your terminal supports ANSI colors
- Try a different terminal emulator (most modern terminals support colors)

## Customization Ideas

### Add timestamp
```python
# In main(), add before model:
from datetime import datetime
components.append(datetime.now().strftime("🕐%H:%M"))
```

### Show messages count
```python
# In main(), add after cost:
if usage_data:
    messages_text = f"📨{usage_data['messages_count']}"
    components.append(messages_text)
```

### Change number formatting
```python
# Modify format_number() function to show more precision:
def format_number(num: float) -> str:
    if num >= 1000000:
        return f"{num/1000000:.2f}M"  # Changed from .1f to .2f
    elif num >= 1000:
        return f"{num/1000:.1f}k"
    else:
        return f"{num:.0f}"
```

### Adjust session window
```python
# Change from 5 hours to 3 hours in analyze_usage_data():
cutoff_time = datetime.now(timezone.utc) - timedelta(hours=3)  # Changed from 5

# Also update in calculate_reset_time():
session_end = session_start + timedelta(hours=3)  # Changed from 5
```

## Related Projects

- [claude-code-usage-bar](https://github.com/leeguooooo/claude-code-usage-bar) - Terminal usage bar with token monitoring (inspiration for token tracking)
- [ccstatusline](https://github.com/sirmalloc/ccstatusline) - Powerline support and themes
- [claude-powerline](https://github.com/Owloops/claude-powerline) - Vim-style powerline
- [claude-code-statusline](https://github.com/rz1989s/claude-code-statusline) - Atomic precision statusline with MCP monitoring

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Author

Created by Harald Schilly

## Links

- [Claude Code Documentation](https://code.claude.com/docs/en/statusline)
- [GitHub Repository](https://github.com/haraldschilly/claude-statusline)
- [Report Issues](https://github.com/haraldschilly/claude-statusline/issues)
