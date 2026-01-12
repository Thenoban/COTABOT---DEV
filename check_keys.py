import requests
import json

try:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://mysquadstats.com/"
    }
    url = "https://api.mysquadstats.com/seasonleaderboards?mod=Vanilla&search=76561198357026569&season=current" 
    # Used a different ID from logs or random if previous one had no data for some fields
    # But 76561198370120720 seemed to have data. Let's use that one.
    url = "https://api.mysquadstats.com/seasonleaderboards?mod=Vanilla&search=76561198370120720&season=current"

    r = requests.get(url, headers=headers)
    data = r.json()
    
    if data.get("data"):
        player = data["data"][0]
        # keys = sorted(player.keys())
        # print("KEYS:", keys)
        
        # Specific check
        print("Score:", player.get("seasonScore"), player.get("totalScore"))
        print("Kills:", player.get("seasonKills"), player.get("totalKills"))
        print("Deaths:", player.get("seasonDeaths"), player.get("totalDeaths"))
        print("Revives:", player.get("seasonRevives"), player.get("totalRevives"))
        print("Wounds:", player.get("seasonWounds"), player.get("totalWounds"))
        print("KD:", player.get("seasonKdRatio"), player.get("totalKdRatio"))
        
        print(json.dumps(player, indent=2))
    else:
        print("No data found")

except Exception as e:
    print(e)
