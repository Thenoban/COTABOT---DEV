# Clean up corrupted file - keep only until async def setup

with open(r"\\192.168.1.174\cotabot\COTABOT - DEV\cogs\squad_players.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find async def setup line
setup_line = None
for i, line in enumerate(lines):
    if "async def setup" in line:
        setup_line = i
        break

if setup_line:
    # Keep everything up to and including the setup function (usually 3-4 lines)
    # Find the end of setup function (next blank line or function)
    end_line = setup_line + 10  # Safety: keep next 10 lines after setup
    
    for i in range(setup_line + 1, min(setup_line + 20, len(lines))):
        # Look for end of setup function
        if lines[i].strip() == "" or (lines[i].startswith("def ") or lines[i].startswith("class ")):
            end_line = i
            break
    
    clean_lines = lines[:end_line]
    
    # Write clean file
    with open(r"\\192.168.1.174\cotabot\COTABOT - DEV\cogs\squad_players.py", "w", encoding="utf-8") as f:
        f.writelines(clean_lines)
    
    print(f"✅ Cleaned file: kept {len(clean_lines)} lines (removed {len(lines) - len(clean_lines)} corrupt lines)")
else:
    print("❌ Could not find 'async def setup'")
