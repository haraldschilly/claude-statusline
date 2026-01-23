#!/usr/bin/env python3
"""
Demo script to visualize the statusline without running Claude Code
"""

# ANSI color codes
RESET = '\033[0m'
GREEN = '\033[32m'
ORANGE = '\033[38;5;208m'
RED = '\033[91m'
BOLD = '\033[1m'
GREEN_BG = '\033[42m\033[30m'
ORANGE_BG = '\033[48;5;208m\033[30m'
RED_BG = '\033[41m\033[30m'
BOLD_GREEN = '\033[1;32m'
BOLD_RED = '\033[1;31m'


def progress_bar(percentage, width=8):
    """Create a colored progress bar."""
    if percentage >= 90:
        color = RED
    elif percentage >= 80:
        color = ORANGE
    else:
        color = GREEN

    filled = int((percentage / 100) * width)
    empty = width - filled
    bar = '█' * filled + '░' * empty
    return f"{color}{bar}{RESET}"


def demo():
    """Show examples of the statusline at different usage levels."""
    print(f"\n{BOLD}Claude Code Statusline Demo{RESET}")
    print("=" * 70)
    print()

    examples = [
        {
            "title": "Normal Usage (Green)",
            "git": f"origin/main {GREEN_BG}[A1]{RESET} {ORANGE_BG}[M2]{RESET} {BOLD_GREEN}+45{RESET} {BOLD_RED}-12{RESET}",
            "ctx": 30,
            "daily": 15,
            "weekly": 38,
            "model": "Sonnet 4.5"
        },
        {
            "title": "With Pull Request",
            "git": f"origin/feature-auth {ORANGE_BG}[M3]{RESET}",
            "pr": "PR#123: Add user authentication",
            "ctx": 62,
            "daily": 25,
            "weekly": 55,
            "model": "Opus 4.5"
        },
        {
            "title": "High Usage - Warning (Orange)",
            "git": f"origin/main {GREEN_BG}[A5]{RESET} {BOLD_GREEN}+87{RESET}",
            "ctx": 82,
            "daily": 85,
            "weekly": 88,
            "model": "Sonnet 4.5"
        },
        {
            "title": "Critical Usage (Red)",
            "git": f"origin/hotfix {ORANGE_BG}[M2]{RESET} {RED_BG}[D1]{RESET} {BOLD_GREEN}+23{RESET} {BOLD_RED}-45{RESET}",
            "ctx": 95,
            "daily": 93,
            "weekly": 96,
            "model": "Opus 4.5"
        },
        {
            "title": "Not in a Git Repository",
            "ctx": 45,
            "daily": 30,
            "weekly": 42,
            "model": "Sonnet 4.5"
        }
    ]

    for example in examples:
        print(f"{BOLD}{example['title']}{RESET}")

        components = []

        # Git info
        if 'git' in example:
            components.append(example['git'])

        # PR info
        if 'pr' in example:
            components.append(example['pr'])

        # Context
        ctx_bar = progress_bar(example['ctx'], width=8)
        components.append(f"ctx:{ctx_bar}")

        # Model usage
        daily_bar = progress_bar(example['daily'], width=8)
        weekly_bar = progress_bar(example['weekly'], width=8)
        components.append(f"{example['model']}@{daily_bar}/{weekly_bar}")

        statusline = " | ".join(components)
        print(f"  {statusline}")
        print()

    print("=" * 70)
    print()
    print(f"{BOLD}Progress Bar Colors:{RESET}")
    print(f"  {GREEN}██████░░{RESET} Green  (0-79%)  - Normal usage")
    print(f"  {ORANGE}██████░░{RESET} Orange (80-89%) - Approaching limit")
    print(f"  {RED}███████░{RESET} Red    (90-100%) - Critical usage")
    print()
    print(f"{BOLD}File Status Badges:{RESET}")
    print(f"  {GREEN_BG}[A#]{RESET} Added files (green background)")
    print(f"  {ORANGE_BG}[M#]{RESET} Modified files (orange background)")
    print(f"  {RED_BG}[D#]{RESET} Deleted files (red background)")
    print()
    print(f"{BOLD}Line Changes:{RESET}")
    print(f"  {BOLD_GREEN}+NN{RESET} Lines added (bold green)")
    print(f"  {BOLD_RED}-NN{RESET} Lines removed (bold red)")
    print()
    print(f"{BOLD}Components:{RESET}")
    print(f"  • Git: remote/branch [A#] [M#] [D#] +lines -lines")
    print(f"  • PR: PR#number: title")
    print(f"  • Context: ctx:[progress bar]")
    print(f"  • Usage: ModelName@[daily]/[weekly]")
    print()


if __name__ == "__main__":
    demo()
