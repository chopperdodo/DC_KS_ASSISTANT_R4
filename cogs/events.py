import discord
from discord import app_commands
from discord.ext import commands
import datetime
import database
import re
from typing import Optional

class EventDetailsModal(discord.ui.Modal, title="Event Details / 活動詳情"):
    event_time = discord.ui.TextInput(
        label="Time (UTC) [Format: YYYY-MM-DD HH:MM]",
        placeholder="2025-10-20 14:00",
        min_length=10,
        max_length=16
    )

    description = discord.ui.TextInput(
        label="Description / 描述",
        style=discord.TextStyle.paragraph,
        placeholder="Additional details... / 更多細節...",
        required=False,
        max_length=1000
    )

    def __init__(self, name, event_type, repeat_interval, icon_url, color_hex, mode="create", event_id=None, default_time=None, default_desc=None):
        super().__init__()
        self.name = name
        self.event_type = event_type
        self.repeat_interval = repeat_interval
        self.icon_url = icon_url
        self.color_hex = color_hex
        self.mode = mode
        self.event_id = event_id
        
        if default_time:
            self.event_time.default = default_time
        if default_desc:
            self.description.default = default_desc

    async def on_submit(self, interaction: discord.Interaction):
        # Validate Time
        try:
            time_str = self.event_time.value.strip()
            if len(time_str) <= 11: # Assume MM-DD HH:MM
                dt_no_year = datetime.datetime.strptime(time_str, "%m-%d %H:%M")
                current_year = datetime.datetime.now().year
                start_time = dt_no_year.replace(year=current_year)
            else:
                start_time = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            await interaction.response.send_message("❌ Invalid time format. Please use `YYYY-MM-DD HH:MM`.", ephemeral=True)
            return

        # Save to DB
        if self.mode == "create":
            await database.add_event(
                interaction.guild.id, self.name, start_time, self.description.value,
                self.event_type, None, self.repeat_interval, self.icon_url, self.color_hex
            )
            # Create Loop Instances
            if self.repeat_interval:
                current_time = start_time
                delta = None
                match = re.match(r"(\d+)([dhm])", self.repeat_interval)
                if match:
                    amount = int(match.group(1))
                    unit = match.group(2)
                    if unit == 'd': delta = datetime.timedelta(days=amount)
                    elif unit == 'h': delta = datetime.timedelta(hours=amount)
                    elif unit == 'm': delta = datetime.timedelta(minutes=amount)
                
                if delta:
                     for _ in range(5):
                        current_time += delta
                        await database.add_event(
                            interaction.guild.id, self.name, current_time, self.description.value,
                            self.event_type, None, self.repeat_interval, self.icon_url, self.color_hex
                        )

        elif self.mode == "edit":
            if self.event_id:
                await database.delete_event(self.event_id)
            await database.add_event(
                 interaction.guild.id, self.name, start_time, self.description.value,
                self.event_type, None, self.repeat_interval, self.icon_url, self.color_hex
            )

        # Confirm
        msg = f"✅ Event **{self.name}** saved!\nStart: <t:{int(start_time.replace(tzinfo=datetime.timezone.utc).timestamp())}:F>"
        await interaction.response.edit_message(content=msg, view=None)


class EventCreationView(discord.ui.View):
    def __init__(self, mode="create", event_id=None, default_values=None):
        super().__init__(timeout=180)
        self.mode = mode
        self.event_id = event_id
        self.selected_name = None
        self.selected_repeat = None
        
        # Defaults
        self.default_time = None
        self.default_desc = None
        
        # Handle Defaults
        if default_values:
            self.default_time = default_values.get('time')
            self.default_desc = default_values.get('description')
            def_name = default_values.get('name')
            def_repeat = default_values.get('repeat')
            
            # Iterate children to find Selects
            for child in self.children:
                if isinstance(child, discord.ui.Select):
                    # Check partial placeholder text to identify which select it is
                    if "Event Name" in child.placeholder or "活動名稱" in child.placeholder:
                        if def_name:
                            self.selected_name = def_name
                            for option in child.options:
                                if option.value == def_name:
                                    option.default = True
                                    
                    elif "Repeat" in child.placeholder or "重複" in child.placeholder:
                         if def_repeat:
                            self.selected_repeat = def_repeat
                            for option in child.options:
                                if option.value == def_repeat:
                                    option.default = True

    @discord.ui.select(placeholder="Select Event Name (Type) / 選擇活動名稱", options=[
        discord.SelectOption(label="⚔️ KvK & Castle / KvK & 王城戰", value="KvK & Castle / KvK & 王城戰"),
        discord.SelectOption(label="🐻 Bear / 熊", value="Bear / 熊"),
        discord.SelectOption(label="🗡️ Swordland / 聖劍", value="Swordland / 聖劍"),
        discord.SelectOption(label="🏳️‍⚧️ Tri-Alliance / 三盟", value="Tri-Alliance / 三盟"),
        discord.SelectOption(label="🏯 Sanctuary / 遺跡", value="Sanctuary / 遺跡"),
        discord.SelectOption(label="🧑‍🦲 Viking / 維京", value="Viking / 維京"),
        discord.SelectOption(label="🆚 Arena / 競技場", value="Arena / 競技場"),
        discord.SelectOption(label="🎣 Fishing / 釣魚", value="Fishing / 釣魚"),
        discord.SelectOption(label="🛡️ Shield / 護盾", value="Shield / 護盾"),
        discord.SelectOption(label="🌽 Farm / 採集", value="Farm / 採集"),
        discord.SelectOption(label="📅 General / 一般", value="General / 一般")
    ])
    async def select_type_item(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_name = select.values[0]
        await interaction.response.defer()

    @discord.ui.select(placeholder="Repeat / 重複", options=[
        discord.SelectOption(label="None / 無", value="None"),
        discord.SelectOption(label="Daily / 每日", value="1d"),
        discord.SelectOption(label="Every 2 Days / 每兩天", value="2d"),
        discord.SelectOption(label="Weekly / 每週", value="7d"),
        discord.SelectOption(label="Bi-Weekly / 每兩週", value="14d"),
        discord.SelectOption(label="Every 4 Hours (Shield)", value="4h"),
        discord.SelectOption(label="Every 8 Hours (Shield)", value="8h"),
    ])
    async def select_repeat_item(self, interaction: discord.Interaction, select: discord.ui.Select):
        val = select.values[0]
        self.selected_repeat = None if val == "None" else val
        await interaction.response.defer()

    @discord.ui.button(label="Next / 下一步", style=discord.ButtonStyle.primary, emoji="➡️")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_name:
            await interaction.response.send_message("❌ Please select an Event Name first.", ephemeral=True)
            return

        # Determine Color/Icon based on selected Name (which is also Type)
        color_hex = 0x3498db # Blue
        icon_url = "https://img.icons8.com/color/96/calendar--v1.png"
        
        name = self.selected_name
        
        if "Shield" in name:
            color_hex = 0xe74c3c
            icon_url = "https://img.icons8.com/color/96/shield.png"
        elif "Arena" in name:
             color_hex = 0xe74c3c
             icon_url = "https://img.icons8.com/color/96/boxing-glove.png"
        elif "KvK" in name or "Swordland" in name or "Tri-Alliance" in name:
             color_hex = 0xe74c3c
             icon_url = "https://img.icons8.com/color/96/sword.png"
        elif "Sanctuary" in name:
             color_hex = 0x9b59b6
             icon_url = "https://img.icons8.com/color/96/ruins.png"
        elif "Bear" in name:
             color_hex = 0xe67e22
             icon_url = "https://img.icons8.com/color/96/bear.png"
        elif "Fishing" in name: # Specific check before Farm
             color_hex = 0x2ecc71
             icon_url = "https://img.icons8.com/color/96/fishing-pole.png"
        elif "Farm" in name:
            color_hex = 0x2ecc71
            icon_url = "https://img.icons8.com/color/96/field.png"
        elif "Viking" in name:
            color_hex = 0xf1c40f
            icon_url = "https://img.icons8.com/color/96/viking-helmet.png"

        modal = EventDetailsModal(
            name=self.selected_name,
            event_type=self.selected_name, # Name is Type
            repeat_interval=self.selected_repeat,
            icon_url=icon_url,
            color_hex=color_hex,
            mode=self.mode,
            event_id=self.event_id,
            default_time=self.default_time,
            default_desc=self.default_desc
        )
        await interaction.response.send_modal(modal)


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Register context menu
        self.ctx_menu = app_commands.ContextMenu(
            name="Edit Event",
            callback=self.edit_event_context,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def edit_event_context(self, interaction: discord.Interaction, message: discord.Message):
        if not message.embeds:
            await interaction.response.send_message("Target message has no event info.", ephemeral=True)
            return

        embed = message.embeds[0]
        event_id = None
        for field in embed.fields:
             if "ID" in field.name and "Repeat" in field.name:
                 try:
                     val = field.value
                     id_part = val.split("|")[0].strip()
                     event_id = int(id_part.replace("`", ""))
                     break
                 except:
                     continue
        
        if not event_id:
             await interaction.response.send_message("❌ Could not find Event ID.", ephemeral=True)
             return
             
        await self.launch_edit(interaction, event_id)

    @app_commands.command(name="update", description="Update an event by ID")
    async def update_event_command(self, interaction: discord.Interaction, event_id: int):
        await self.launch_edit(interaction, event_id)

    async def launch_edit(self, interaction: discord.Interaction, event_id: int):
        events = await database.get_all_events(interaction.guild.id)
        target = next((e for e in events if e['id'] == event_id), None)
        
        if not target:
            await interaction.response.send_message("❌ Event not found.", ephemeral=True)
            return

        # Prepare Defaults
        def_name = target['name']
        
        # Legacy mapping if needed
        type_map = {
            "KvK & Castle": "KvK & Castle / KvK & 王城戰",
            "Bear": "Bear / 熊",
            "Swordland": "Swordland / 聖劍",
            "Tri-Alliance": "Tri-Alliance / 三盟",
            "Sanctuary": "Sanctuary / 遺跡",
            "Viking": "Viking / 維京",
            "Arena": "Arena / 競技場",
            "Fishing": "Fishing / 釣魚",
            "Shield": "Shield / 護盾",
            "Farm": "Farm / 採集",
            "General": "General / 一般"
        }
        if def_name in type_map:
             def_name = type_map[def_name]
             
        # Format time to remove seconds if present (YYYY-MM-DD HH:MM:SS -> YYYY-MM-DD HH:MM)
        time_val = target['event_time']
        if time_val and len(time_val) > 16:
            time_val = time_val[:16]

        defaults = {
            'time': time_val,
            'description': target['description'] or "",
            'name': def_name,
            'repeat': target['repeat_config'] or "None"
        }
        
        view = EventCreationView(mode="edit", event_id=event_id, default_values=defaults)
        await interaction.response.send_message(
            f"🛠️ **Updating Event #{event_id}**\nPlease select the new Name and Repeat settings, then click Next.", 
            view=view, 
            ephemeral=True
        )

    @app_commands.command(name="set_channel", description="Set announcement channel (Admin)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.guild: return
        await database.set_guild_channel(interaction.guild.id, channel.id)
        await interaction.response.send_message(f"✅ Channel set to {channel.mention}.")

    @app_commands.command(name="add", description="Add a new event")
    async def add_event_command(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "🆕 **Create New Event**\nPlease select the Event Name and Repeat settings below.", 
            view=EventCreationView(), 
            ephemeral=True
        )

    @app_commands.command(name="list", description="List upcoming events")
    @app_commands.describe(limit="Number of events (default 5, max 20)")
    async def list_events(self, interaction: discord.Interaction, limit: int = 5):
        if not interaction.guild: return
        limit = max(1, min(limit, 20))

        events = await database.get_all_events(interaction.guild.id)
        if not events:
            await interaction.response.send_message("No upcoming events.", ephemeral=True)
            return

        embeds = []
        for event in events[:limit]:
            try:
                dt = datetime.datetime.strptime(event['event_time'], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                dt = datetime.datetime.strptime(event['event_time'], "%Y-%m-%d %H:%M:%S.%f")
            
            unix_ts = int(dt.replace(tzinfo=datetime.timezone.utc).timestamp())
            
            # Use DB values directly since we save bilingual names now
            # But apply legacy map just in case
            type_map = {
                "KvK & Castle": "KvK & Castle / KvK & 王城戰",
                "Bear": "Bear / 熊",
                "Swordland": "Swordland / 聖劍",
                "Tri-Alliance": "Tri-Alliance / 三盟",
                "Sanctuary": "Sanctuary / 遺跡",
                "Viking": "Viking / 維京",
                "Arena": "Arena / 競技場",
                "Fishing": "Fishing / 釣魚",
                "Shield": "Shield / 護盾",
                "Farm": "Farm / 採集",
                "General": "General / 一般"
            }
            e_type = event['event_type'] if event['event_type'] else "General"
            e_type = type_map.get(e_type, e_type)
            
            color = event['color_hex'] if event['color_hex'] else 0x3498db
            icon = event['icon_url'] if event['icon_url'] else "https://img.icons8.com/color/96/calendar--v1.png"
            
            # Since Name is effectively Type now, we just show Name
            # But the user might have custom description
            # Title: "Bear / 熊" (as stored in Name)
            
            embed = discord.Embed(
                title=f"{event['name']}", 
                description=event['description'] or "No description", 
                color=color
            )
            embed.set_thumbnail(url=icon)
            embed.add_field(name="⏰ Time / 時間", value=f"<t:{unix_ts}:F>\n<t:{unix_ts}:R>", inline=True)
            
            repeat_str = event['repeat_config'] if event['repeat_config'] else "None"
            embed.add_field(name="🆔 ID | 🔄 Repeat", value=f"`{event['id']}` | `{repeat_str}`", inline=False)
            embeds.append(embed)
        
        await interaction.response.send_message(embeds=embeds)

    @app_commands.command(name="delete", description="Delete an event")
    async def delete_event(self, interaction: discord.Interaction, event_id: int):
        await database.delete_event(event_id)
        await interaction.response.send_message(f"🗑️ Deleted event {event_id}.")

async def setup(bot):
    await bot.add_cog(Events(bot))
