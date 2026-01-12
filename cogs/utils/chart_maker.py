
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

import numpy as np

def generate_profile_card(player_data, avatar_bytes=None):
    """
    Generates a player profile card using Matplotlib.
    player_data: dict containing 'name', 'rank', 'stats'
    avatar_bytes: bytes of the discord avatar overlay
    """
    from PIL import Image
    import io as io_module
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axis('off')
    bg_color = '#2f3136'
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    
    name = player_data.get('name', 'Unknown')
    ax.text(0.5, 0.9, name, ha='center', va='top', fontsize=28, weight='bold', color='white')
    
    rank = player_data.get('rank', 'Üye')
    ax.text(0.5, 0.82, rank, ha='center', va='top', fontsize=16, color='#b9bbbe')
    
    if avatar_bytes:
        try:
            avatar_img = Image.open(io_module.BytesIO(avatar_bytes))
            avatar_ax = fig.add_axes([0.05, 0.65, 0.2, 0.2])
            avatar_ax.imshow(avatar_img)
            avatar_ax.axis('off')
        except:
            pass
    
    stats = player_data.get('stats', {})
    stat_items = list(stats.items())
    
    def draw_stat(label, value, x, y, color='white'):
        ax.text(x, y, label, ha='center', fontsize=12, color='#8e9297')
        ax.text(x, y-0.08, str(value), ha='center', fontsize=18, weight='bold', color=color)
    
    if len(stat_items) >= 4:
        draw_stat(stat_items[0][0], stat_items[0][1], 0.2, 0.55, '#FFD700')
        draw_stat(stat_items[1][0], stat_items[1][1], 0.4, 0.55, '#43b581')
        draw_stat(stat_items[2][0], stat_items[2][1], 0.6, 0.55, '#f04747')
        draw_stat(stat_items[3][0], stat_items[3][1], 0.8, 0.55, '#7289da')
        
        if len(stat_items) >= 8:
            draw_stat(stat_items[4][0], stat_items[4][1], 0.2, 0.30)
            draw_stat(stat_items[5][0], stat_items[5][1], 0.4, 0.30)
            draw_stat(stat_items[6][0], stat_items[6][1], 0.6, 0.30)
            draw_stat(stat_items[7][0], stat_items[7][1], 0.8, 0.30)
    
    ax.text(0.5, 0.05, '🎮 Squad Stats Profile', ha='center', fontsize=10, color='#72767d')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.1, facecolor=bg_color)
    buf.seek(0)
    plt.close()
    return buf

def generate_report_charts(deltas, period="weekly"):
    """Generate comprehensive report charts with 4 visualizations in 2x2 grid."""
    if not deltas or len(deltas) == 0:
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.text(0.5, 0.5, '📊 Henüz veri yok\n\nİlk snapshot alındıktan sonra\nrapor görselleştirilecek.', ha='center', va='center', fontsize=20, color='#888888')
        ax.axis('off')
        fig.patch.set_facecolor('#2f3136')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='#2f3136')
        buf.seek(0)
        plt.close(fig)
        return buf
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    fig.patch.set_facecolor('#2f3136')
    COLORS = {"score": "#FFD700", "kills": "#FF4444", "kd_old": "#4169E1", "kd_new": "#32CD32", "improved": "#00FF00", "declined": "#FF0000", "stable": "#FFA500"}
    
    top_score = sorted([d for d in deltas if d.get('score_delta', 0) > 0], key=lambda x: x.get('score_delta', 0), reverse=True)[:10]
    if top_score:
        names = [p['name'][:15] for p in top_score]
        scores = [p.get('score_delta', 0) for p in top_score]
        ax1.barh(names, scores, color=COLORS["score"], edgecolor='white', linewidth=0.5)
        ax1.set_xlabel('Score Artışı', color='white', fontsize=12)
        ax1.set_title(f'📈 En Çok Gelişenler - Score ({period.capitalize()})', color='white', fontsize=14, fontweight='bold', pad=15)
        ax1.set_facecolor('#40444b')
        ax1.tick_params(colors='white')
        ax1.spines['bottom'].set_color('white')
        ax1.spines['left'].set_color('white')
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.grid(axis='x', alpha=0.3, color='white')
        ax1.invert_yaxis()
        for i, v in enumerate(scores):
            ax1.text(v + max(scores)*0.02, i, f'{v:,.0f}', va='center', color='white', fontsize=10, fontweight='bold')
    else:
        ax1.text(0.5, 0.5, 'Veri Yok', ha='center', va='center', color='#888888', fontsize=16)
        ax1.axis('off')
        ax1.set_facecolor('#40444b')
    
    top_kills = sorted([d for d in deltas if d.get('kills_delta', 0) > 0], key=lambda x: x.get('kills_delta', 0), reverse=True)[:10]
    if top_kills:
        names_k = [p['name'][:15] for p in top_kills]
        kills = [p.get('kills_delta', 0) for p in top_kills]
        ax2.barh(names_k, kills, color=COLORS["kills"], edgecolor='white', linewidth=0.5)
        ax2.set_xlabel('Kill Artışı', color='white', fontsize=12)
        ax2.set_title(f'🎯 En Çok Gelişenler - Kills ({period.capitalize()})', color='white', fontsize=14, fontweight='bold', pad=15)
        ax2.set_facecolor('#40444b')
        ax2.tick_params(colors='white')
        ax2.spines['bottom'].set_color('white')
        ax2.spines['left'].set_color('white')
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.grid(axis='x', alpha=0.3, color='white')
        ax2.invert_yaxis()
        for i, v in enumerate(kills):
            ax2.text(v + max(kills)*0.02, i, f'{v:,.0f}', va='center', color='white', fontsize=10, fontweight='bold')
    else:
        ax2.text(0.5, 0.5, 'Veri Yok', ha='center', va='center', color='#888888', fontsize=16)
        ax2.axis('off')
        ax2.set_facecolor('#40444b')
    
    top_kd = sorted([d for d in deltas if d.get('kd_new', 0) > 0], key=lambda x: x.get('kd_new', 0), reverse=True)[:5]
    if top_kd and all(d.get('kd_old') is not None for d in top_kd):
        names_kd = [p['name'][:12] for p in top_kd]
        kd_old_vals = [p.get('kd_old', 0) for p in top_kd]
        kd_new_vals = [p.get('kd_new', 0) for p in top_kd]
        x = np.arange(len(names_kd))
        width = 0.35
        ax3.bar(x - width/2, kd_old_vals, width, label='Önceki', color=COLORS["kd_old"], edgecolor='white', linewidth=0.5)
        ax3.bar(x + width/2, kd_new_vals, width, label='Şimdi', color=COLORS["kd_new"], edgecolor='white', linewidth=0.5)
        ax3.set_ylabel('K/D Oranı', color='white', fontsize=12)
        ax3.set_title(f'⚔️ K/D Değişimi - Top 5 ({period.capitalize()})', color='white', fontsize=14, fontweight='bold', pad=15)
        ax3.set_xticks(x)
        ax3.set_xticklabels(names_kd, rotation=30, ha='right', color='white')
        ax3.tick_params(colors='white')
        ax3.set_facecolor('#40444b')
        ax3.spines['bottom'].set_color('white')
        ax3.spines['left'].set_color('white')
        ax3.spines['top'].set_visible(False)
        ax3.spines['right'].set_visible(False)
        ax3.grid(axis='y', alpha=0.3, color='white')
        ax3.legend(facecolor='#40444b', edgecolor='white', labelcolor='white', fontsize=10)
        for i, (old, new) in enumerate(zip(kd_old_vals, kd_new_vals)):
            ax3.text(i - width/2, old + 0.05, f'{old:.2f}', ha='center', color='white', fontsize=9)
            ax3.text(i + width/2, new + 0.05, f'{new:.2f}', ha='center', color='white', fontsize=9)
    else:
        ax3.text(0.5, 0.5, 'Veri Yok', ha='center', va='center', color='#888888', fontsize=16)
        ax3.axis('off')
        ax3.set_facecolor('#40444b')
    
    improved = len([d for d in deltas if d.get('score_delta', 0) > 100])
    declined = len([d for d in deltas if d.get('score_delta', 0) < -100])
    stable = len(deltas) - improved - declined
    if improved + declined + stable > 0:
        sizes = [improved, stable, declined]
        labels = ['Gelişenler', 'Sabit', 'Düşenler']
        colors_pie = [COLORS["improved"], COLORS["stable"], COLORS["declined"]]
        explode = (0.05, 0, 0)
        wedges, texts, autotexts = ax4.pie(sizes, explode=explode, labels=labels, colors=colors_pie, autopct='%1.1f%%', shadow=True, startangle=90, textprops={'color': 'white', 'fontsize': 12})
        for autotext in autotexts:
            autotext.set_color('black')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(11)
        ax4.set_title(f'📊 Performans Dağılımı ({period.capitalize()})', color='white', fontsize=14, fontweight='bold', pad=15)
        ax4.set_facecolor('#40444b')
    else:
        ax4.text(0.5, 0.5, 'Veri Yok', ha='center', va='center', color='#888888', fontsize=16)
        ax4.axis('off')
        ax4.set_facecolor('#40444b')
    
    plt.tight_layout(pad=2.0)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#2f3136', edgecolor='none')
    buf.seek(0)
    plt.close(fig)
    return buf
