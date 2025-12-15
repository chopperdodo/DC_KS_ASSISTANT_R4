import discord
from discord import app_commands
from discord.ext import commands
import datetime
import database
import re
from typing import Optional
from constants import EventConfig

class EventDetailsModal(discord.ui.Modal, title="Event Details / 活動詳情"):
    event_time = discord.ui.TextInput(
        label="Time (UTC) [Format: YYYY-MM-DD HH:MM]",
        placeholder="2025-10-20 14:00",
        min_length=10,
        max_length=16
    )

    duration = discord.ui.TextInput(
        label="Duration (mins) / 持續時間 (分鐘)",
        placeholder="60",
        min_length=1,
        max_length=4,
        required=True
    )

    description = discord.ui.TextInput(
        label="Description / 描述",
        style=discord.TextStyle.paragraph,
        placeholder="Additional details... / 更多細節...",
        required=False,
        max_length=1000
    )

    def __init__(self, name, event_type, repeat_interval, icon_url, color_hex, mode="create", event_id=None, default_time=None, default_desc=None, default_duration=0):
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
        self.duration.default = str(default_duration)

    async def on_submit(self, interaction: discord.Interaction):
        try:
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

            # Validate Duration
            try:
                duration_mins = int(self.duration.value.strip())
            except ValueError:
                await interaction.response.send_message("❌ Invalid duration. Please enter a number.", ephemeral=True)
                return

            # Save to DB
            if self.mode == "create":
                await database.add_event(
                    interaction.guild.id, self.name, start_time, self.description.value,
                    self.event_type, None, self.repeat_interval, self.icon_url, self.color_hex, duration_mins
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
                                self.event_type, None, self.repeat_interval, self.icon_url, self.color_hex, duration_mins
                            )

            elif self.mode == "edit":
                if self.event_id:
                    await database.delete_event(self.event_id)
                await database.add_event(
                     interaction.guild.id, self.name, start_time, self.description.value,
                    self.event_type, None, self.repeat_interval, self.icon_url, self.color_hex, duration_mins
                )

            # Confirm & Check Conflicts
            msg = f"✅ Event **{self.name}** saved!\nStart: <t:{int(start_time.replace(tzinfo=datetime.timezone.utc).timestamp())}:F>"
            
            # Conflict Detection Logic
            new_start = start_time
            new_end = start_time + datetime.timedelta(minutes=duration_mins)
            
            events = await database.get_all_events(interaction.guild.id)
            conflicts = []
            
            for e in events:
                try:
                    e_start = datetime.datetime.strptime(e['event_time'], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    e_start = datetime.datetime.strptime(e['event_time'], "%Y-%m-%d %H:%M:%S.%f")
                
                # Duration default 0 if column null (handled by migration but be safe)
                e_dur = e['duration'] if 'duration' in e.keys() else 0
                e_end = e_start + datetime.timedelta(minutes=e_dur)

                if e['name'] == self.name and abs((e_start - start_time).total_seconds()) < 1:
                    continue 
                
                if (new_start < e_end) and (new_end > e_start):
                    conflicts.append(e)

            if conflicts:
                msg += "\n\n⚠️ **CONFLICT DETECTED / 與其他事件有衝突**\n"
                for c in conflicts[:3]:
                    c_time = c['event_time']
                    msg += f"- **{c['name']}** at `{c_time}`\n"

            await interaction.response.edit_message(content=msg, view=None)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error saving event: {str(e)}", ephemeral=True)
            print(f"ERROR in on_submit: {e}")
            import traceback
            traceback.print_exc()


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
        self.default_duration = None
        
        # Generate Options dynamically
        self.type_options = []
        for name, data in EventConfig.EVENTS.items():
            self.type_options.append(discord.SelectOption(
                label=f" {name}" if not name.startswith(("⚔️","🐻","🗡️","🏳️‍⚧️","🏯","🧑‍🦲","🆚","🎣","🛡️","🌽","📅")) else name, 
                # ^ Some names have chars, some don't. The constants file keys have emojis? 
                # Wait, I put keys as "KvK & Castle / KvK & 王城戰" in constants. But in original code they had emojis in label.
                # Let's just use the key as value. Label can be Key too for now or add emojis in Constants? 
                # I'll stick to Value = Key. 
                # Actually, duplicate emojis might be annoying. Let's fix constants or just use Key.
                # For now, simplistic approach: Value is the Key.
                value=name,
                description=data.get("desc", "")
            ))
            
            # Note: In previous code, I had emojis in labels like "⚔️ KvK...". 
            # If I want to keep that polish, I should probably store "label" in constants too.
            # But user asked to consolidate libraries. 
            # For this iteration, I will assume the keys in constants match the desired VALUE.
            # I can add emojis manually here or update constant keys.
            # I will trust the keys in constants.py roughly match what we had.

        # Add proper emojis to labels for UX polish if missing
        # Mapping simple heuristic
        friendly_labels = []
        for name, data in EventConfig.EVENTS.items():
            emoji = ""
            if "KvK" in name: emoji = "⚔️ "
            elif "Bear" in name: emoji = "🐻 "
            elif "Swordland" in name: emoji = "🗡️ "
            elif "Tri-Alliance" in name: emoji = "🏳️‍⚧️ "
            elif "Sanctuary" in name: emoji = "🏯 "
            elif "Viking" in name: emoji = "🧑‍🦲 "
            elif "Arena" in name: emoji = "🆚 "
            elif "Fishing" in name: emoji = "🎣 "
            elif "Shield" in name: emoji = "🛡️ "
            elif "Farm" in name: emoji = "🌽 "
            elif "General" in name: emoji = "📅 "
            
            friendly_labels.append(discord.SelectOption(
                label=f"{emoji}{name}", 
                value=name, 
                description=data.get("desc", "")
            ))
        
        # Dynamically set options for the Select item
        # We need to find the select item or init it dynamically? 
        # Discord Views define items at Class level usually. 
        # But we can replace options in __init__.
        
        # Find the type select
        self.select_type_item.options = friendly_labels

        # Handle Defaults
        if default_values:
            self.default_time = default_values.get('time')
            self.default_desc = default_values.get('description')
            self.default_duration = default_values.get('duration')
            def_name = default_values.get('name')
            def_repeat = default_values.get('repeat')
            
            # Iterate children to find Selects
            for child in self.children:
                if isinstance(child, discord.ui.Select):
                    # Check partial placeholder
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

    # Placeholder options, will be replaced in __init__
    @discord.ui.select(placeholder="Select Event Name (Type) / 選擇活動名稱", options=[
        discord.SelectOption(label="Loading...", value="loading") 
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

        # Determine Color/Icon using Constants
        color_hex, icon_url = EventConfig.get_event_metadata(self.selected_name)
        default_dur = EventConfig.get_event_duration(self.selected_name)
        
        # Override with stored default if editing
        if self.default_duration is not None:
             default_dur = self.default_duration

        modal = EventDetailsModal(
            name=self.selected_name,
            event_type=self.selected_name, # Name is Type
            repeat_interval=self.selected_repeat,
            icon_url=icon_url,
            color_hex=color_hex,
            mode=self.mode,
            event_id=self.event_id,
            default_time=self.default_time,
            default_desc=self.default_desc,
            default_duration=default_dur
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
        
        # Legacy mapping using Constants
        mapping = EventConfig.get_legacy_mapping()
        if def_name in mapping:
             def_name = mapping[def_name]
             
        # Format time to remove seconds if present (YYYY-MM-DD HH:MM:SS -> YYYY-MM-DD HH:MM)
        time_val = target['event_time']
        if time_val and len(time_val) > 16:
            time_val = time_val[:16]

        defaults = {
            'time': time_val,
            'description': target['description'] or "",
            'name': def_name,
            'repeat': target['repeat_config'] or "None",
            'duration': target['duration'] if 'duration' in target.keys() else 0
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
        mapping = EventConfig.get_legacy_mapping()
        
        # Pre-process ALL events for conflict check (O(N^2) but N=20 max due to limit? No, limit is display, we need all for robust check)
        # Actually, verifying against *upcoming* events is enough.
        # Let's check overlap within the displayed set + any others fetched?
        # get_all_events returns everything sorted by time.
        
        for i, event in enumerate(events[:limit]):
            try:
                dt = datetime.datetime.strptime(event['event_time'], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                dt = datetime.datetime.strptime(event['event_time'], "%Y-%m-%d %H:%M:%S.%f")
            
            unix_ts = int(dt.replace(tzinfo=datetime.timezone.utc).timestamp())
            
            e_type = event['event_type'] if event['event_type'] else "General"
            e_type = mapping.get(e_type, e_type)
            
            color, icon = EventConfig.get_event_metadata(e_type)
            
            # Check for conflict with ANY other event in the full list
            has_conflict = False
            my_dur = event['duration'] if 'duration' in event.keys() else 0
            my_end = dt + datetime.timedelta(minutes=my_dur)
            
            for other in events:
                if other['id'] == event['id']: continue
                
                try:
                    o_dt = datetime.datetime.strptime(other['event_time'], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    o_dt = datetime.datetime.strptime(other['event_time'], "%Y-%m-%d %H:%M:%S.%f")
                
                o_dur = other['duration'] if 'duration' in other.keys() else 0
                o_end = o_dt + datetime.timedelta(minutes=o_dur)
                
                # Overlap check
                if (dt < o_end) and (my_end > o_dt):
                    has_conflict = True
                    break
            
            title_prefix = ""
            if has_conflict:
                title_prefix = "⚠️ [CONFLICT] "
                color = 0xff0000 # Red override
            
            embed = discord.Embed(
                title=f"{title_prefix}{event['name']}", 
                description=event['description'] or "No description", 
                color=color
            )
            embed.set_thumbnail(url=icon)
            embed.add_field(name="⏰ Time / 時間", value=f"<t:{unix_ts}:F>\n<t:{unix_ts}:R>", inline=True)
            
            repeat_str = event['repeat_config'] if event['repeat_config'] else "None"
            dur_str = f"{my_dur}m" if my_dur > 0 else "N/A"
            embed.add_field(name="🆔 ID | 🔄 Repeat | ⏳ Dur", value=f"`{event['id']}` | `{repeat_str}` | `{dur_str}`", inline=False)
            
            if has_conflict:
                 embed.set_footer(text="Conflict with other events / 與其他事件有衝突")
            
            embeds.append(embed)
        
        await interaction.response.send_message(embeds=embeds)

    @app_commands.command(name="delete", description="Delete an event")
    async def delete_event(self, interaction: discord.Interaction, event_id: int):
        await database.delete_event(event_id)
        await interaction.response.send_message(f"🗑️ Deleted event {event_id}.")

async def setup(bot):
    await bot.add_cog(Events(bot))
