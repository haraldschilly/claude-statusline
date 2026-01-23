#!/bin/bash
#
# Installation script for Claude Code Statusline
# https://github.com/haraldschilly/claude-statusline
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CLAUDE_DIR="$HOME/.claude"
STATUSLINE_SCRIPT="$CLAUDE_DIR/statusline.py"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"

echo "🚀 Installing Claude Code Statusline..."
echo ""

# Make the script executable
chmod +x "$SCRIPT_DIR/statusline.py"
echo "✓ Made statusline.py executable"

# Create symlink
if [ -L "$STATUSLINE_SCRIPT" ]; then
    echo "⚠ Symlink already exists at $STATUSLINE_SCRIPT"
    read -p "  Replace it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm "$STATUSLINE_SCRIPT"
        ln -s "$SCRIPT_DIR/statusline.py" "$STATUSLINE_SCRIPT"
        echo "✓ Symlink updated"
    else
        echo "⊘ Keeping existing symlink"
    fi
elif [ -f "$STATUSLINE_SCRIPT" ]; then
    echo "⚠ File already exists at $STATUSLINE_SCRIPT"
    read -p "  Back it up and create symlink? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        mv "$STATUSLINE_SCRIPT" "$STATUSLINE_SCRIPT.backup"
        ln -s "$SCRIPT_DIR/statusline.py" "$STATUSLINE_SCRIPT"
        echo "✓ Backup created at $STATUSLINE_SCRIPT.backup"
        echo "✓ Symlink created"
    else
        echo "⊘ Keeping existing file"
    fi
else
    ln -s "$SCRIPT_DIR/statusline.py" "$STATUSLINE_SCRIPT"
    echo "✓ Symlink created at $STATUSLINE_SCRIPT"
fi

# Check settings.json
echo ""
if [ -f "$SETTINGS_FILE" ]; then
    if grep -q '"statusLine"' "$SETTINGS_FILE"; then
        echo "✓ Statusline already configured in settings.json"
    else
        echo "⚠ Adding statusLine configuration to settings.json"
        # Create a backup
        cp "$SETTINGS_FILE" "$SETTINGS_FILE.backup"
        echo "✓ Backup created at $SETTINGS_FILE.backup"

        # Add statusLine config (before the final closing brace)
        if command -v jq &> /dev/null; then
            # Use jq if available
            jq '. + {"statusLine": {"type": "command", "command": "~/.claude/statusline.py", "padding": 0}}' "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp"
            mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"
            echo "✓ Configuration added using jq"
        else
            echo ""
            echo "⚠ Please add this to your $SETTINGS_FILE manually:"
            echo ""
            echo '  "statusLine": {'
            echo '    "type": "command",'
            echo '    "command": "~/.claude/statusline.py",'
            echo '    "padding": 0'
            echo '  }'
            echo ""
        fi
    fi
else
    echo "⚠ Settings file not found at $SETTINGS_FILE"
    echo "  Creating settings file with statusLine configuration..."
    cat > "$SETTINGS_FILE" << 'EOF'
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/statusline.py",
    "padding": 0
  }
}
EOF
    echo "✓ Settings file created"
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Restart Claude Code for changes to take effect"
echo "   2. (Optional) Install gh CLI for PR info: sudo apt install gh"
echo "   3. (Optional) Customize limits in statusline.py (lines 212-213)"
echo ""
echo "📖 Documentation: $SCRIPT_DIR/README.md"
echo "🐛 Issues: https://github.com/haraldschilly/claude-statusline/issues"
echo ""
echo "🎉 Enjoy your new statusline!"
