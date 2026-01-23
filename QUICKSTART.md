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

### Visual Elements

**Progress Bars** (8 chars wide)
- 🟢 Green: 0-79% (normal)
- 🟠 Orange: 80-89% (warning)
- 🔴 Red: 90-100% (critical)

**File Status Badges**
- `[A#]` - Added files (green background)
- `[M#]` - Modified files (orange background)
- `[D#]` - Deleted files (red background)

**Line Changes**
- `+NN` - Lines added (bold green)
- `-NN` - Lines removed (bold red)

### Example Output

```
origin/main [A3] [M1] [D2] +45 -12 | PR#123: Add auth | ctx:███░░░░░ | Sonnet@█░░░░░░░/███░░░░░
```

## Customization

### Change Usage Limits
Edit `statusline.py` lines 212-213:
```python
daily_limit = 2000
weekly_limit = 10000
```

### Change Progress Bar Width
Edit lines 251, 259-260:
```python
progress_bar(context_used, width=10)  # Change 8 to 10
```

### Change Color Thresholds
Edit lines 154-160:
```python
if percentage >= 90:  # Red at 90%
    color = RED
elif percentage >= 80:  # Orange at 80%
    color = ORANGE
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
