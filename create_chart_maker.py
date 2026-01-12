import sys

# Read LIVE clean file
with open(r"\\192.168.1.174\cotabot\COTABOT - DEV\cogs\utils\chart_maker_new.py", "r", encoding="utf-8") as f:
    content = f.read()

# Append numpy import and two functions
additional_code = '''
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
        ax.text(0.5, 0.5, '📊 Henüz veri yok\\n\\nİlk snapshot alındıktan sonra\\nrapor görselleştirilecek.', ha='center', va='center', fontsize=20, color='#888888')
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
'''

# Write combined file
with open(r"\\192.168.1.174\cotabot\COTABOT - DEV\cogs\utils\chart_maker.py", "w", encoding="utf-8") as f:
    f.write(content)
    f.write(additional_code)

print("✅ chart_maker.py successfully created with all 4 functions!")
print("Functions: generate_activity_image, generate_live_server_image, generate_profile_card, generate_report_charts")
