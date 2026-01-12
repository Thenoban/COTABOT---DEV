# COTABOT Centralized Configuration

# Bot Administrators (User IDs)
# 305072157170466816 = Bot Owner / Main Admin
ADMIN_USER_IDS = [305072157170466816]

# Authorized Roles for Management Commands (e.g. !squad_sync, !panel_yonet, !bot_durum)
ADMIN_ROLE_IDS = [
    1156683624972824726, # Admin Role 1
    1169089828449693696, # Admin Role 2
    1133107024847192084, # Admin Role 3
    1246107060429656198, # Admin Role 4
    1458469299005030571  # Admin Role 5
]

# Clan Member Roles (Used for scanning squad stats and events)
CLAN_MEMBER_ROLE_IDS = [
    1161912948344754248, # Member Role 1
    1151960296185942127, # Member Role 2
    1246107421135601826  # Member Role 3
]

# Manager User IDs (Can manage events, moderate features)
# Same as ADMIN for now, can be customized later
MANAGER_USER_IDS = ADMIN_USER_IDS

# Manager Role IDs (Can manage events)
# Same as ADMIN for now, can be customized later
MANAGER_ROLE_IDS = ADMIN_ROLE_IDS

# BattleMetrics Configuration
BM_API_URL = "https://api.battlemetrics.com"
SERVER_ID = "19262595"
BM_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbiI6ImZkNjFiNGUwNDg3NGVhOWMiLCJpYXQiOjE3Njc3ODQxMjMsIm5iZiI6MTc2Nzc4NDEyMywiaXNzIjoiaHR0cHM6Ly93d3cuYmF0dGxlbWV0cmljcy5jb20iLCJzdWIiOiJ1cm46dXNlcjoxMDUzOTEzIn0.jZ78RBn-O0_njNeGIJZlVrWXk5ptMdQ8bIFBgEsfmzw"


# Google Sheets Config
# DEVELOPMENT MODE: Sheet sync disabled to protect production data
GOOGLE_SHEET_KEY = None 

# Environment Flag
DEV_MODE = True

class COLORS:
    DEFAULT = 0x2B2D31   # Dark Theme
    SUCCESS = 0x57F287   # Green
    ERROR = 0xED4245     # Red
    WARNING = 0xFEE75C   # Yellow
    INFO = 0x5865F2      # Blue
    SQUAD = 0x117D37     # Squad Dark Green
    GOLD = 0xF1C40F      # Gold (Leaderboards)
    ORANGE = 0xE67E22    # Orange
    BLUE = 0x3498DB      # Blue (Alternative Info)
    GREEN = 0x2ECC71     # Green (Standard)

