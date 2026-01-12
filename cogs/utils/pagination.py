import discord

class PaginationView(discord.ui.View):
    def __init__(self, data, title="Liste", page_size=10, embed_creator=None, refresh_callback=None):
        super().__init__(timeout=None)  # No timeout - permanent buttons
        self.data = data
        self.title = title
        self.page_size = page_size
        self.embed_creator = embed_creator
        self.refresh_callback = refresh_callback  # Async function to refresh data
        self.current_page = 0
        self.total_pages = max(1, (len(data) + page_size - 1) // page_size)
        
        # Update button states
        self.update_buttons()

    def update_buttons(self):
        self.first_page_btn.disabled = (self.current_page == 0)
        self.prev_page_btn.disabled = (self.current_page == 0)
        self.next_page_btn.disabled = (self.current_page == self.total_pages - 1)
        self.last_page_btn.disabled = (self.current_page == self.total_pages - 1)
        
        self.page_counter_btn.label = f"{self.current_page + 1}/{self.total_pages}"

    def get_current_embed(self):
        start = self.current_page * self.page_size
        end = start + self.page_size
        page_items = self.data[start:end]
        
        if self.embed_creator:
            return self.embed_creator(page_items, self.current_page, self.total_pages)
        else:
            # Default Embed
            embed = discord.Embed(title=self.title, color=discord.Color.blue())
            desc = ""
            for i, item in enumerate(page_items, start + 1):
                desc += f"**{i}.** {str(item)}\n"
            embed.description = desc
            embed.set_footer(text=f"Sayfa {self.current_page + 1}/{self.total_pages}")
            return embed

    @discord.ui.button(label="⏮️", style=discord.ButtonStyle.secondary, row=0)
    async def first_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary, row=0)
    async def prev_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.gray, disabled=True, row=0)
    async def page_counter_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary, row=0)
    async def next_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.secondary, row=0)
    async def last_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = self.total_pages - 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    @discord.ui.button(label="🔄", style=discord.ButtonStyle.success, row=1)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh data and update view"""
        if not self.refresh_callback:
            await interaction.response.send_message("⚠️ Yenileme fonksiyonu tanımlı değil.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Call refresh callback to get new data
            new_data = await self.refresh_callback()
            
            if new_data:
                self.data = new_data
                self.total_pages = max(1, (len(new_data) + self.page_size - 1) // self.page_size)
                
                # Reset to first page if current page is now out of bounds
                if self.current_page >= self.total_pages:
                    self.current_page = 0
                
                self.update_buttons()
                await interaction.followup.edit_message(
                    message_id=interaction.message.id,
                    embed=self.get_current_embed(),
                    view=self
                )
            else:
                await interaction.followup.send("⚠️ Veri yenilenemedi.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Yenileme hatası: {e}", ephemeral=True)
    
    @discord.ui.button(label="🗑️", style=discord.ButtonStyle.danger, row=1)
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
