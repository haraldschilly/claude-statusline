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

**Real Rate-Limit Usage** (Pro/Max subscriptions)
- 🔋 One double-row bar: top half = 5-hour window, bottom half = weekly window, plus the 5h reset countdown: `🔋███▄     3h12m`
- Percentages appear only from 90% on, in red
- Exact numbers from Claude Code (same as `/usage`), no estimation

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
my-project | origin/main A3 M1 D2 +45 -12 | 🧠 ███░░░░░ | 🔋██▄      3h12m | 🤖 Sonnet 4.5 ▃ medium
```

## Customization

### Change Progress Bar Width
Pass a different `width`:
```python
limits_text = format_rate_limits(rate_limits, width=10)  # in main()
```

### Change Color Thresholds
In `bar_color()` (shared by all bars):
```python
if percentage >= 90:      # Red threshold (default: 90%)
    return RED
if percentage >= 80:      # Orange threshold (default: 80%)
    return ORANGE
return GREEN
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
