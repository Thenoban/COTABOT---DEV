# Phase 3 Commands to add after report_cmd

@commands.command(name='export_report')
async def export_report_cmd(self, ctx, period: str = "weekly", format: str = "excel"):
    """
    Raporu dışa aktar.
    Kullanım: !1export_report <weekly|monthly> <excel|pdf>
    """
    if not await self.check_permissions(ctx): return
    
    valid_periods = ["weekly", "monthly"]
    if period not in valid_periods:
        await ctx.send(f"⚠️ Geçersiz dönem. Seçenekler: {', '.join(valid_periods)}")
        return
    
    valid_formats = ["excel", "pdf"]
    if format not in valid_formats:
        await ctx.send(f"⚠️ Geçersiz format. Seçenekler: {', '.join(valid_formats)}")
        return
    
    await ctx.send(f"📊 {period.capitalize()} raporu {format} olarak hazırlanıyor...")
    
    try:
        deltas = self._calculate_deltas(period)
        
        if not deltas:
            await ctx.send(f"⚠️ {period.capitalize()} için veri bulunamadı.")
            return
        
        if format == "excel":
            buf = await asyncio.to_thread(self._export_to_excel, period, deltas)
            
            if buf:
                now = datetime.datetime.now().strftime("%Y%m%d")
                filename = f"{period}_report_{now}.xlsx"
                file = discord.File(buf, filename=filename)
                await ctx.send(f"✅ Excel raporu hazır!", file=file)
            else:
                await ctx.send("❌ Excel oluşturulamadı.")
        
        elif format == "pdf":
            buf = await self._export_to_pdf(period, deltas)
            
            if buf:
                now = datetime.datetime.now().strftime("%Y%m%d")
                filename = f"{period}_report_{now}.pdf"
                file = discord.File(buf, filename=filename)
                await ctx.send(f"✅ PDF raporu hazır!", file=file)
            else:
                await ctx.send("❌ PDF oluşturulamadı.")
    
    except Exception as e:
        await ctx.send(f"❌ Export hatası: {e}")
        logger.error(f"Export error: {e}", exc_info=True)


@commands.command(name='hall_of_fame', aliases=['hof', 'sampiyonlar'])
async def hall_of_fame_cmd(self, ctx):
    """Hall of Fame - Şampiyonlar listesi"""
    
    report_db = self._get_report_db()
    hof = report_db.get("hall_of_fame", {})
    
    if not hof or not any(hof.values()):
        await ctx.send("📜 Henüz Hall of Fame verisi yok. İlk rapor sonrası oluşacak.")
        return
    
    embed = discord.Embed(
        title="🏆 HALL OF FAME - ŞAMPIYONLAR",
        description="En başarılı oyuncular ve rekorlar",
        color=discord.Color.gold(),
        timestamp=datetime.datetime.now()
    )
    
    # Weekly Champions
    weekly_champs = hof.get("weekly_champions", {})
    if weekly_champs:
        top_3 = sorted(weekly_champs.items(), key=lambda x: x[1], reverse=True)[:3]
        champ_text = "\n".join([
            f"{'🥇' if i==0 else '🥈' if i==1 else '🥉'} **{name}** - {count} hafta"
            for i, (name, count) in enumerate(top_3)
        ])
        embed.add_field(name="📅 En Çok Haftalık Şampiyon", value=champ_text, inline=False)
    
    # Monthly Champions
    monthly_champs = hof.get("monthly_champions", {})
    if monthly_champs:
        top_3 = sorted(monthly_champs.items(), key=lambda x: x[1], reverse=True)[:3]
        champ_text = "\n".join([
            f"{'🥇' if i==0 else '🥈' if i==1 else '🥉'} **{name}** - {count} ay"
            for i, (name, count) in enumerate(top_3)
        ])
        embed.add_field(name="📆 En Çok Aylık Şampiyon", value=champ_text, inline=False)
    
    # Records
    records = hof.get("records", {})
    if records:
        record_text = ""
        
        if "highest_weekly_score" in records:
            r = records["highest_weekly_score"]
            record_text += f"🎯 **En Yüksek Score:** {r['player']} - {r['score']:,} ({r['date']})\n"
        
        if "highest_kills_week" in records:
            r = records["highest_kills_week"]
            record_text += f"💀 **En Çok Kill:** {r['player']} - {r['kills']} ({r['date']})"
        
        if record_text:
            embed.add_field(name="📊 Rekorlar", value=record_text, inline=False)
    
    embed.set_footer(text="🏆 Tebrikler tüm şampiyonlara!")
    
    await ctx.send(embed=embed)
