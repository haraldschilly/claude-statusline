# Claude Code Statusline

A beautiful, informative statusline for [Claude Code](https://claude.com/code) with visual progress bars, git integration, and PR status.

## Features

✨ **Visual Progress Bars** - Color-coded ASCII bars that change from green → orange → red as limits approach
🎨 **Smart Color Coding** - Green (0-79%), Orange (80-89%), Red (90-100%)
📊 **Context Window Tracking** - Real-time visualization of your context usage
🔄 **Git Integration** - Shows branch, remote, file status (M/A/D), and line changes
🔀 **Pull Request Info** - Displays PR number and title (via `gh` CLI)
📈 **Usage Statistics** - Daily and weekly message count tracking
⚡ **Fast & Lightweight** - Pure Python, no external dependencies

## Preview

```bash
# Normal usage (green):
origin/main M2/A1 +45 -12 | ctx:███░░░░░ | Sonnet 4.5@█░░░░░░░/███░░░░░

# With Pull Request:
origin/feature | PR#123: Add authentication | ctx:█████░░░ | Opus@██░░░░░░/████░░░░

# Warning level (orange bars at 80%):
ctx:██████░░ | Sonnet@██████░░/███████░

# Critical level (red bars at 90%+):
ctx:███████░ | Sonnet@███████░/████████
```

## Components

| Component | Description | Example |
|-----------|-------------|---------|
| **Git Info** | Remote/branch, colored file status badges, line changes | `origin/main [A3] [M1] +45 -12` |
| **PR Status** | Pull request number and title (requires `gh` CLI) | `PR#123: Add new feature` |
| **Context** | Current session context window usage with visual bar | `ctx:███░░░░░` |
| **Model Usage** | Model name with daily/weekly usage bars | `Sonnet 4.5@█░░░░░░░/███░░░░░` |

### File Status Badge Colors

- 🟢 **[A#]** - Added files (green background)
- 🟠 **[M#]** - Modified files (orange background)
- 🔴 **[D#]** - Deleted files (red background)

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

### Adjust Usage Limits

The default limits are 2000 messages/day and 10000 messages/week. Edit `statusline.py` lines 212-213:

```python
daily_limit = 2000    # Your preferred daily message limit
weekly_limit = 10000  # Your preferred weekly message limit
```

### Customize Progress Bars

**Change bar width** (lines 251, 259-260):
```python
ctx_bar = progress_bar(context_used, width=10)  # Change from 8 to 10
```

**Adjust color thresholds** (lines 154-160):
```python
if percentage >= 90:      # Red threshold (default: 90%)
    color = RED
elif percentage >= 80:    # Orange threshold (default: 80%)
    color = ORANGE
else:
    color = GREEN
```

**Use different characters** (line 167):
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
4. Calculates usage statistics from `~/.claude/stats-cache.json`
5. Generates colored progress bars
6. Outputs the formatted statusline

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
from datetime import datetime

def get_time():
    return datetime.now().strftime("%H:%M")

# In main(), add:
components.append(get_time())
```

### Add session cost
```python
# In main()
cost = data.get('cost', {}).get('total_cost_usd', 0)
if cost > 0:
    components.append(f"${cost:.4f}")
```

### Add token counts
```python
# In main()
total_tokens = (data.get('context_window', {}).get('total_input_tokens', 0) +
                data.get('context_window', {}).get('total_output_tokens', 0))
components.append(f"{total_tokens:,}tk")
```

## Related Projects

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
