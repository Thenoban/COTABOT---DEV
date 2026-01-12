import json
import os

def test_resolution():
    if not os.path.exists("squad_db.json"):
        print("DB Not Found")
        return

    with open("squad_db.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    players = data.get("players", [])
    query = "『COTA』WHO IS DIGGY"
    q_str = str(query).strip()
    
    print(f"Testing Query: '{q_str}'")
    print(f"Hex Query: {q_str.encode('utf-8').hex()}")

    # Clean logic
    clean_q = q_str.replace("『COTA』", "").replace("[COTA]", "").replace("COTA |", "").strip()
    print(f"Cleaned Query: '{clean_q}'")
    
    found = False
    
    print(f"Total Players Loaded: {len(players)}")
    
    # Simulate DB Scan
    for p in players:
        p_name = p.get("name", "NO_NAME")
        
        # Check specific name if we know it
        if "DIG" in p_name or "WHO" in p_name:
            print(f"\nCandidate in DB: '{p_name}'")
            print(f"Hex DB: {p_name.encode('utf-8').hex()}")
            
            # Test Logic
            # B. Name Match
            if p_name.lower() == q_str.lower():
                print("-> Match: Exact Original")
                found = True
            if p_name.lower() == clean_q.lower():
                print("-> Match: Exact Clean")
                found = True
            
            # C. Startswith
            if p_name.lower().startswith(q_str.lower()):
                print("-> Match: Startswith Original")
                found = True
            if p_name.lower().startswith(clean_q.lower()):
                print("-> Match: Startswith Clean")
                found = True

            # D. Containment
            if q_str.lower() in p_name.lower():
                print("-> Match: In DB Name (Original)")
                found = True
            if clean_q.lower() in p_name.lower():
                print("-> Match: In DB Name (Clean)")
                found = True

            # E. Reverse Containment
            if len(p_name) > 3 and p_name.lower() in q_str.lower():
                 print("-> Match: Reverse Containment")
                 found = True

    if found:
        print("\nSUCCESS: Match found with current logic.")
    else:
        print("\nFAILURE: No match found with current logic.")

if __name__ == "__main__":
    test_resolution()
