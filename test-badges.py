#!/usr/bin/env python3
"""Test script to show colored badges"""

# ANSI color codes
GREEN_BG = '\033[42m\033[30m'  # Green background, black text
ORANGE_BG = '\033[48;5;208m\033[30m'  # Orange background, black text
RED_BG = '\033[41m\033[30m'  # Red background, black text
RESET = '\033[0m'

print("\nColored File Status Badges:")
print("=" * 60)
print()

print(f"Added files:    {GREEN_BG}A3{RESET}")
print(f"Modified files: {ORANGE_BG}M1{RESET}")
print(f"Deleted files:  {RED_BG}D2{RESET}")
print()

print("Example statuslines:")
print()
print(f"origin/main {GREEN_BG}A3{RESET} {ORANGE_BG}M1{RESET} +45 -12")
print(f"origin/feature {ORANGE_BG}M5{RESET} {RED_BG}D2{RESET} +102 -87")
print(f"local/dev {GREEN_BG}A1{RESET} +23")
print()
