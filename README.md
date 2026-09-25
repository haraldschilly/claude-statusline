# Claude Code Statusline

A beautiful, informative statusline for [Claude Code](https://claude.com/code) with real subscription rate-limit usage, visual progress bars, git integration, and reset countdowns.

## Features

- 🔋 **Real Rate-Limit Usage** - Exact 5-hour and 7-day subscription usage, as reported by Claude Code itself
- 📊 **Visual Progress Bars** - Color-coded bars that change from green → orange → red as limits approach; 5h and 7d limits share one compact two-row bar (`█`/`▀`/`▄`)
- ⏱️ **Reset Countdowns** - Time remaining until each rate-limit window resets
- 🎨 **Colored File Badges** - File status with colored backgrounds: 🟢 A# 🟠 M# 🔴 D#
- 💚 **Bold Line Changes** - Line additions in bold green (+NN), deletions in bold red (-NN)
- 🎯 **Smart Color Coding** - Green (<80%), Orange (80-89%), Red (≥90%)
- 🔄 **Git Integration** - Shows branch, remote, file status badges, and line changes
- 🔀 **Pull Request Info** - Displays PR number and title (via `gh` CLI)
- ▃ **Effort Level Indicator** - Block bar showing current reasoning effort (▁ low, ▃ medium, ▅ high, ▇ xhigh)
- 📁 **Project Directory** - Shows git root directory name (or working directory) at a glance
- ⚡ **Fast & Lightweight** - Pure Python, no external dependencies, PR lookups cached

## Preview

```bash
# Normal usage (green progress bars, colored badges):
my-project | origin/main A3 M1 +45 -12 | 🧠 ███░░░░░ | 🔋██▄      3h12m | 🤖 Sonnet 4.5 ▃ medium
# A3 = green background, M1 = orange background
# +45 = bold green, -12 = bold red

# With Pull Request:
my-app | origin/feature M2 | PR#123: Add authentication | 🧠 █████░░░ | 🔋████▄    2h15m | 🤖 Opus ▅ high

# Warning level (orange bars at 80%+):
my-project | origin/hotfix A5 D1 +102 -87 | 🧠 ██████░░ | 🔋██████▀  1h30m | 🤖 Sonnet ▃ medium

# Critical level (red bars at 90%+):
my-project | origin/bugfix M3 D2 +23 -45 | 🧠 ███████░ | 🔋███████  0h22m 5h 93% 7d 90% 0d09h | 🤖 Sonnet ▁ low
```

## Components

| Component | Description | Example |
|-----------|-------------|---------|
| **Directory** | Git root directory basename (or working directory) | `my-project` |
| **Git Info** | Remote/branch, colored file status badges, line changes | `origin/main A3 M1 +45 -12` |
| **PR Status** | Pull request number and title (requires `gh` CLI) | `PR#123: Add new feature` |
| **Context** | Current session context window usage with visual bar | `🧠 ███░░░░░` |
| **Rate Limits** | Double-row bar: top half = 5-hour window, bottom half = 7-day window; plus 5h reset countdown | `🔋███▄     3h12m` |
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

The effort level is taken from Claude Code's stdin JSON (`effort.level`), falling back to the `CLAUDE_CODE_EFFORT_LEVEL` environment variable, then `~/.claude/settings.json` (`effortLevel` key). Change it mid-session with `/effort low|medium|high|xhigh`.

### Rate-Limit Tracking

Claude Code passes the subscription rate limits to the statusline on stdin (`rate_limits` field) — the same numbers `/usage` shows:

- **5h**: `rate_limits.five_hour.used_percentage` and `resets_at`
- **7d**: `rate_limits.seven_day.used_percentage` and `resets_at`

Both windows share one 8-character bar: top half = 5h window, bottom half = 7d window. Where both are filled it shows `█`, then `▀` (5h further) or `▄` (7d further), then blanks. The bar has a single color, from the higher of the two values (green/orange/red). Percentages are only spelled out, in red, once a window reaches 90% (for the 7d window together with its reset countdown).

The field is only present for claude.ai Pro/Max subscribers, and only after the first API response in a session. When it is absent (e.g. API-key usage, or right after startup), the rate-limit blocks are simply hidden.

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

### Customize Progress Bars

**Change bar width** (search for `width=8` in `main()`):
```python
limits_text = format_rate_limits(rate_limits, width=10)  # in main(), rate-limit bar
```

**Adjust color thresholds** (in `bar_color()`, shared by all bars):
```python
if percentage >= 90:      # Red threshold (default: 90%)
    return RED
if percentage >= 80:      # Orange threshold (default: 80%)
    return ORANGE
return GREEN
```

**Use different characters** (in `progress_bar()` function):
```python
bar = '█' * filled + '░' * empty  # Try: ▓/▒, ■/□, ●/○, ═/─, etc.
```

### PR Title Length

PR titles and branch names are truncated automatically to fit the terminal width (see the adaptive truncation loop at the end of `main()`).

PR lookups via `gh` are cached for `PR_CACHE_TTL` seconds (default 60) per repository and branch in `~/.cache/claude-statusline/pr-cache.json`.

### Hide Components

Remove the corresponding entries from `render()` in `main()`.

## How It Works

Claude Code calls your statusline script periodically, passing context information via stdin as JSON:

```json
{
  "model": {"display_name": "Sonnet 4.5"},
  "workspace": {"current_dir": "/path/to/project"},
  "context_window": {"used_percentage": 42.5},
  "effort": {"level": "high"},
  "rate_limits": {
    "five_hour": {"used_percentage": 23.5, "resets_at": 1738425600},
    "seven_day": {"used_percentage": 41.2, "resets_at": 1738857600}
  }
}
```

The script:
1. Extracts model, effort, context, and rate-limit info from the JSON
2. Queries git status from the current directory (a single `git status --porcelain=v2 --branch` plus a diff)
3. Checks for GitHub PR info (if `gh` CLI is available; cached for 60s)
4. Generates colored progress bars and reset countdowns
5. Truncates branch/PR title to fit the terminal width and outputs the statusline

### Data Sources

- **Context window, rate limits, effort**: From Claude Code's JSON input (stdin)
- **Git info**: From git commands in workspace directory
- **PR info**: From `gh` CLI (GitHub API), cached

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

### Rate limits not showing
- Only available for claude.ai Pro/Max subscriptions
- They appear after the first API response of a session

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

### Show session cost
```python
# In main(), add to render():
cost = (data.get('cost') or {}).get('total_cost_usd')
if cost is not None:
    parts.append(f"💰${cost:.2f}")
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
