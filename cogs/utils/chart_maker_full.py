
import matplotlib.pyplot as plt
import pandas as pd
import io

# Fix for Headless Environments (Docker/Linux)
plt.switch_backend('Agg')

def generate_activity_image(stats_list):
    """
    Generates a dark-themed table image from the stats list.
    stats_list: List of dicts [{'name': '...', 'daily': 120, 'weekly': 500, 'monthly': 2000}, ...]
    returns: BytesIO object containing the PNG
    """
    
    # Pre-process data
    if not stats_list:
        df = pd.DataFrame(columns=["Sıra", "Oyuncu", "Günlük", "Haftalık", "Aylık"])
        df.loc[0] = ["-", "Veri Yok", "-", "-", "-"]
    else:
        data = []
        for i, s in enumerate(stats_list[:15], 1): # Top 15
            name = s['name'][:18] # Truncate long names
            
            def fmt(m):
                if m < 60: return f"{int(m)}dk"
                return f"{int(m)//60}sa {int(m)%60}dk"
                
            rank_str = str(i)
            if i == 1: rank_str = "🥇"
            elif i == 2: rank_str = "🥈"
            elif i == 3: rank_str = "🥉"
            
            data.append([rank_str, name, fmt(s['daily']), fmt(s['weekly']), fmt(s['monthly'])])
            
        df = pd.DataFrame(data, columns=["Sıra", "Oyuncu", "Günlük", "Haftalık", "Aylık"])

    # Setup Plot
    plt.figure(figsize=(10, len(df) * 0.6 + 1.5)) # Dynamic height
    plt.axis('off')
    
    # Dark Background
    plt.gcf().set_facecolor('#2f3136') # Discord Dark Gray
    
    # Table Colors
    cell_text = []
    cell_colors = []
    
    # Custom color function
    colors_list = []
    for i in range(len(df)):
        if i == 0: bg = '#4f3b00' # Gold-ish tint
        elif i == 1: bg = '#3d4045' # Slightly lighter
        elif i == 2: bg = '#3d342b' # Bronze-ish
        else: bg = '#2f3136' 
        colors_list.append([bg]*5)

    # Create Table
    tbl = plt.table(
        cellText=df.values,
        colLabels=df.columns,
        cellLoc='center',
        loc='center',
        cellColours=colors_list,
        colColours=['#202225']*5 
    )

    # Styling
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(14)
    tbl.scale(1.2, 2) # W, H scaling

    # Column Widths
    # Rank: small, Name: big, others: medium
    # This is tricky with auto layout, but let's try fixed logic if needed or let auto handle it
    
    # Header Styling
    for (row, col), cell in tbl.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold', color='white')
            cell.set_edgecolor('#202225')
            cell.set_linewidth(2)
        else:
            cell.set_text_props(color='#dcddde')
            cell.set_edgecolor('#2f3136')
            
            # Highlight Top 3 Text (optional)
            if row == 1: cell.set_text_props(weight='bold', color='#FFD700') # Gold
            elif row == 2: cell.set_text_props(weight='bold', color='#C0C0C0') # Silver
            elif row == 3: cell.set_text_props(weight='bold', color='#CD7F32') # Bronze

    # Title
    plt.title("🏆 SQUAD SUNUCU AKTİFLİK DURUMU (KLAN)", color='white', pad=20, fontsize=16, weight='bold')

    # Save to Buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.5, facecolor='#2f3136')
    buf.seek(0)
    plt.close()
    
    return buf

def generate_live_server_image(server_info, player_list):
    """
    Generates a dashboard image for the live server status.
    server_info: dict {'name': '...', 'players': '50/100', 'queue': '2', 'map': '...'}
    player_list: list of dicts [{'name': '...', 'status_text': 'SES', 'details': 'Channel'}]
    """
    
    # Setup Data
    if not player_list:
        df = pd.DataFrame(columns=["OYUNCU", "DURUM", "KANAL"])
        df.loc[0] = ["-", "YOK", "Çevrimdışı"]
    else:
        data = []
        for p in player_list:
            data.append([p['name'], p['status_text'], p['details']])
        df = pd.DataFrame(data, columns=["OYUNCU", "DURUM", "KANAL"])

    # Dynamic Height
    row_height = 0.6
    header_height = 3.0
    fig_height = header_height + (len(df) * row_height)
    if fig_height < 5: fig_height = 5
    
    plt.figure(figsize=(12, fig_height)) # Wider figure
    plt.axis('off')
    plt.gcf().set_facecolor('#202225') # Darker Discord bg

    # Header Area
    # Server Name
    plt.text(0.5, 0.96, server_info.get('name', 'Squad Server'), ha='center', va='top', 
             fontsize=20, weight='bold', color='white', transform=plt.gca().transAxes)
    
    # Stats Line
    stats_text = f"Harita: {server_info.get('map', '?')}   •   Oyuncular: {server_info.get('players', '0/0')}   •   Sıra: {server_info.get('queue', '0')}"
    plt.text(0.5, 0.89, stats_text, ha='center', va='top', 
             fontsize=14, color='#b9bbbe', transform=plt.gca().transAxes)
    
    # Divider Line
    plt.plot([0.05, 0.95], [0.82, 0.82], color='#40444b', linewidth=2, transform=plt.gca().transAxes)

    # Table Area
    cell_colors = []
    for i in range(len(df)):
        if i % 2 == 0: bg = '#2f3136'
        else: bg = '#292b2f' # Zebra striping
        cell_colors.append([bg]*3)
    
    # Fixed Column Widths
    # Total width ~ 0.9 units
    # Name: 0.45, Status: 0.15, Channel: 0.30
    col_widths = [0.45, 0.15, 0.30]
    
    tbl = plt.table(
        cellText=df.values,
        colLabels=["OYUNCU", "DURUM", "KANAL"],
        cellLoc='left',
        loc='upper center',
        cellColours=cell_colors,
        colColours=['#202225']*3,
        colWidths=col_widths,
        bbox=[0.05, 0.0, 0.9, 0.78] 
    )
    
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(13)
    
    # Custom Styling
    for (row, col), cell in tbl.get_celld().items():
        cell.set_edgecolor('#202225')
        cell.set_height(0.06) # Taller cells
        
        if row == 0:
            cell.set_text_props(weight='bold', color='#dcddde')
            cell.set_facecolor('#202225')
            cell.set_height(0.08)
        else:
            cell.set_text_props(color='white')
            
            # Status Column Coloring
            if col == 1: 
                cell.get_text().set_horizontalalignment('center')
                val = cell.get_text().get_text()
                if val == "SES":
                    cell.set_text_props(color='#43b581', weight='bold') # Green
                elif val == "YOK":
                    cell.set_text_props(color='#f04747', weight='bold') # Red
                elif val == "MUTE":
                    cell.set_text_props(color='#faa61a', weight='bold') # Orange

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.2, facecolor='#202225')
    buf.seek(0)
    plt.close()
    return buf
