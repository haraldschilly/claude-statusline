# Quick Start Guide

## Installation

```bash
# Clone the repo (if not already done)
git clone https://github.com/haraldschilly/claude-statusline.git ~/p/claude-statusline

# Run the installer
~/p/claude-statusline/install.sh
```

Or manually:
```bash
# Create symlink
ln -sf ~/p/claude-statusline/statusline.py ~/.claude/statusline.py

# Add to ~/.claude/settings.json:
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/statusline.py",
    "padding": 0
  }
}
```

## What You Get

### Core Features

**Real Token Tracking**
- 🔋 Token usage with limits: `🔋843.4k/4.2M █░░░░░░░`
- ⏱️ Session countdown: `⏱️ 0h46m` until reset
- 📊 Smart P90 limits (adapts to your usage)

**Progress Bars** (8 chars wide)
- 🟢 Green: <80% (normal)
- 🟠 Orange: 80-89% (warning)
- 🔴 Red: ≥90% (critical)

**File Status Badges**
- `A#` - Added files (green background)
- `M#` - Modified files (orange background)
- `D#` - Deleted files (red background)

**Line Changes**
- `+NN` - Lines added (bold green)
- `-NN` - Lines removed (bold red)

### Example Output

```
origin/main A3 M1 D2 +45 -12 | 🧠███░░░░░ | 🔋843.4k/4.2M █░░░░░░░ | ⏱️ 0h46m | 🤖 Sonnet 4.5
```

## Customization

### Usage Limits (Automatic)
Limits are **automatically calculated** from your usage history (P90 method):
- Analyzes last 8 days of sessions
- Uses 90th percentile as threshold
- Falls back to sensible defaults (19k-220k tokens)

### Change Progress Bar Width
In `main()` function, find `width=8`:
```python
token_bar = progress_bar(token_pct, width=10)  # Change 8 to 10
```

### Change Color Thresholds
In `progress_bar()` function:
```python
if percentage >= 90:  # Red at 90%
    color = RED
elif percentage >= 80:  # Orange at 80%
    color = ORANGE
```

### Adjust Session Window
In `analyze_usage_data()` function:
```python
cutoff_time = datetime.now(timezone.utc) - timedelta(hours=3)  # Change from 5
```

## Testing

```bash
# Run the demo
~/p/claude-statusline/demo.py

# Test badge colors
~/p/claude-statusline/test-badges.py
```

## Updating

```bash
cd ~/p/claude-statusline
git pull
# Changes apply immediately (symlinked)
```

## Requirements

- Python 3 ✅ (required)
- git ⚙️ (optional - for git info)
- gh CLI ⚙️ (optional - for PR info)

## Troubleshooting

**Statusline not showing?**
- Restart Claude Code
- Check symlink: `ls -la ~/.claude/statusline.py`
- Test script: `echo '{"context_window":{"used_percentage":50},"model":{"display_name":"Test"},"workspace":{"current_dir":"'$(pwd)'"}}' | ~/.claude/statusline.py`

**Colors not working?**
- Ensure terminal supports ANSI colors
- Most modern terminals work fine

## Links

- 📦 GitHub: https://github.com/haraldschilly/claude-statusline
- 📖 Full README: [README.md](README.md)
- 🤝 Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)
- 📄 License: [LICENSE](LICENSE) (MIT)
