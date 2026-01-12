import sys

# Read file
with open(r'\\192.168.1.174\cotabot\COTABOT - DEV\cogs\squad_players.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 2944 (index 2943) - remove 4 extra spaces
if lines[2943].startswith('        embed.set_footer'):
    lines[2943] = '    ' + lines[2943].lstrip()
    print("Fixed line 2944")
else:
    print(f"Line 2944 current: {repr(lines[2943])}")

# Write back
with open(r'\\192.168.1.174\cotabot\COTABOT - DEV\cogs\squad_players.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Done!")
