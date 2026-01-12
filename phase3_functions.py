# Phase 3 Functions: Excel Export, Hall of Fame, PDF Report

# NOTE: Add these as class methods in SquadPlayers class
# Location: After _analyze_trends function

# === Excel Export ===

async def _export_to_excel(self, period, deltas):
    """
    Export report data to Excel file.
    
    Args:
        period (str): "weekly" or "monthly"
        deltas (list): Player delta data
    
    Returns:
        BytesIO: Excel file buffer or None
    """
    if not deltas:
        return None
    
    import pandas as pd
    from openpyxl.styles import Font, PatternFill
    from io import BytesIO
    
    # Prepare data for DataFrame
    data = []
    for p in deltas:
        data.append({
            'Oyuncu': p['name'],
            'Score': p.get('score', 0),
            'Kills': p.get('kills', 0),
            'Deaths': p.get('deaths', 0),
            'K/D': round(p.get('kd', 0), 2),
            'Revives': p.get('revives', 0)
        })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    df = df.sort_values('Score', ascending=False)
    df.insert(0, 'Sıra', range(1, len(df) + 1))
    
    # Create Excel buffer
    buf = BytesIO()
    
    # Write to Excel with formatting
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=f'{period.capitalize()} Report', index=False)
        
        # Get workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets[f'{period.capitalize()} Report']
        
        # Format header
        for cell in worksheet[1]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    cell_len = len(str(cell.value))
                    if cell_len > max_length:
                        max_length = cell_len
                except:
                    pass
            adjusted_width = (max_length + 2)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    buf.seek(0)
    logger.info(f"Excel export created: {len(df)} players")
    return buf


# === Hall of Fame ===

def _update_hall_of_fame(self, period, deltas):
    """
    Update Hall of Fame with report winners.
    
    Args:
        period (str): "weekly" or "monthly"
        deltas (list): Player delta data
    """
    if not deltas:
        return
    
    report_db = self._get_report_db()
    
    # Initialize Hall of Fame structure
    if "hall_of_fame" not in report_db:
        report_db["hall_of_fame"] = {
            "weekly_champions": {},
            "monthly_champions": {},
            "most_improved_awards": {},
            "records": {}
        }
    
    hof = report_db["hall_of_fame"]
    
    # Sort by score
    top_players = sorted(deltas, key=lambda x: x.get('score', 0), reverse=True)
    
    if not top_players:
        return
    
    champion = top_players[0]
    champion_name = champion['name']
    
    # Update champion count
    key = f"{period}_champions"
    if key in hof:
        hof[key][champion_name] = hof[key].get(champion_name, 0) + 1
    
    # Check for records
    highest_score = hof["records"].get("highest_weekly_score", {}).get("score", 0)
    if champion['score'] > highest_score:
        hof["records"]["highest_weekly_score"] = {
            "player": champion_name,
            "score": champion['score'],
            "date": datetime.datetime.now().strftime("%Y-%m-%d")
        }
    
    # Most kills
    top_killer = max(deltas, key=lambda x: x.get('kills', 0))
    highest_kills = hof["records"].get("highest_kills_week", {}).get("kills", 0)
    if top_killer['kills'] > highest_kills:
        hof["records"]["highest_kills_week"] = {
            "player": top_killer['name'],
            "kills": top_killer['kills'],
            "date": datetime.datetime.now().strftime("%Y-%m-%d")
        }
    
    self._save_report_db(report_db)
    logger.info(f"Hall of Fame updated: {champion_name} won {period}")


# === PDF Export ===

async def _export_to_pdf(self, period, deltas):
    """
    Export report to professional PDF.
    
    Args:
        period (str): "weekly" or "monthly"
        deltas (list): Player delta data
    
    Returns:
        BytesIO: PDF file buffer or None
    """
    if not deltas:
        return None
    
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from io import BytesIO
    
    buf = BytesIO()
    
    # Create PDF
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    
    # Container for elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#4472C4'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Title
    period_map = {"weekly": "Haftalık", "monthly": "Aylık"}
    title = Paragraph(f"📊 {period_map.get(period, period.capitalize())} Performans Raporu", title_style)
    elements.append(title)
    
    # Date
    date_str = datetime.datetime.now().strftime("%d %B %Y")
    date_para = Paragraph(f"<b>Rapor Tarihi:</b> {date_str}", styles['Normal'])
    elements.append(date_para)
    elements.append(Spacer(1, 20))
    
    # Top 10 Table
    table_data = [['Sıra', 'Oyuncu', 'Score', 'Kills', 'Deaths', 'K/D', 'Revives']]
    
    for i, p in enumerate(sorted(deltas, key=lambda x: x.get('score', 0), reverse=True)[:10], 1):
        table_data.append([
            str(i),
            p['name'][:20],
            str(p.get('score', 0)),
            str(p.get('kills', 0)),
            str(p.get('deaths', 0)),
            f"{p.get('kd', 0):.2f}",
            str(p.get('revives', 0))
        ])
    
    # Create table
    table = Table(table_data, colWidths=[1.5*cm, 5*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2*cm])
    table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONT NAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Data rows
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 30))
    
    # Summary stats
    total_active = len(deltas)
    avg_score = sum(d.get('score', 0) for d in deltas) / total_active if total_active > 0 else 0
    
    summary_text = f"<b>Özet İstatistikler:</b><br/>"
    summary_text += f"Toplam Aktif Oyuncu: {total_active}<br/>"
    summary_text += f"Ortalama Score: {avg_score:.0f}<br/>"
    
    summary_para = Paragraph(summary_text, styles['Normal'])
    elements.append(summary_para)
    
    # Footer
    elements.append(Spacer(1, 50))
    footer = Paragraph(
        f"<i>Squad Sunucu Raporu - {datetime.datetime.now().strftime('%Y')}</i>",
        styles['Normal']
    )
    elements.append(footer)
    
    # Build PDF
    doc.build(elements)
    
    buf.seek(0)
    logger.info(f"PDF export created: {len(deltas)} players")
    return buf
