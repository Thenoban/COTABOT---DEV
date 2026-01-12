import sys

# Read corrupted file
with open(r"\\192.168.1.174\cotabot\COTABOT - DEV\cogs\utils\chart_maker.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Keep only first 335 lines (before corruption)
clean_lines = lines[:335]

# Write clean file
with open(r"\\192.168.1.174\cotabot\COTABOT - DEV\cogs\utils\chart_maker.py", "w", encoding="utf-8") as f:
    f.writelines(clean_lines)

print("File cleaned - removed corrupted lines from 336 onwards")
