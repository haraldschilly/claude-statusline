# Contributing to Claude Code Statusline

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- A clear, descriptive title
- Steps to reproduce the issue
- Expected vs actual behavior
- Your environment (OS, Python version, Claude Code version)
- Relevant logs or screenshots

### Suggesting Features

Feature suggestions are welcome! Please create an issue describing:
- The feature and its use case
- Why it would be useful
- Potential implementation approach (optional)

### Submitting Pull Requests

1. **Fork the repository** and create a new branch for your feature/fix
2. **Write clear commit messages** describing what changed and why
3. **Test your changes** thoroughly
4. **Update documentation** if you're changing behavior or adding features
5. **Submit a PR** with a clear description of your changes

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/claude-statusline.git
cd claude-statusline

# Make the script executable
chmod +x statusline.py demo.py

# Test your changes
./demo.py

# Test with sample input
echo '{"context_window":{"used_percentage":50},"model":{"display_name":"Test"},"workspace":{"current_dir":"'$(pwd)'"}}' | ./statusline.py
```

### Code Style

- Follow PEP 8 style guidelines
- Use descriptive variable names
- Add docstrings to functions
- Keep functions focused and small
- Comment complex logic

### Testing

Before submitting a PR, test your changes:

```bash
# Test the demo
./demo.py

# Test with various input scenarios
./statusline.py < test_input.json

# Test in different directories (git repo, non-git repo)
```

## Ideas for Contributions

Here are some areas where contributions would be welcome:

### Features
- Add support for more version control systems (Mercurial, SVN)
- Support for GitLab/Bitbucket PR info (in addition to GitHub)
- Configurable color schemes/themes
- Support for custom components via plugins
- More detailed git information (ahead/behind, stash count)
- Integration with other MCP servers

### Improvements
- Better error handling and logging
- Performance optimizations
- Better cross-platform support (Windows, macOS)
- Configuration file support (YAML/TOML)
- More comprehensive tests

### Documentation
- More examples and use cases
- Video tutorials
- Troubleshooting guides
- Localization (translations)

## Questions?

Feel free to open an issue with questions about contributing!

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
