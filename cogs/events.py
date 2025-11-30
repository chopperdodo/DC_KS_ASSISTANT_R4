import discord
from discord import app_commands
from discord.ext import commands
import datetime
import database
import re

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def parse_interval(self, interval_str: str) -> datetime.timedelta:
        """Parses a string like '2d', '12h', '30m' into a timedelta."""
        if not interval_str:
            return None
        
        match = re.match(r"(\d+)([dhm])", interval_str.lower())
        if not match:
            return None
        
        amount = int(match.group(1))
        unit = match.group(2)
        
        if unit == 'd':
            return datetime.timedelta(days=amount)
        elif unit == 'h':
            return datetime.timedelta(hours=amount)
        elif unit == 'm':
            return datetime.timedelta(minutes=amount)
        return None

    async def name_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        options = [
            "Bear-1", "Bear-2",
            "Swordland-legion-1", "Swordland-legion-2",
            "Tri-alliance-legion-1", "Tri-alliance-legion-2",
            "Castle-Battle"
        ]
        return [
            app_commands.Choice(name=option, value=option)
            for option in options if current.lower() in option.lower()
        ]

    @app_commands.command(name="add", description="Add a new event (UTC time)")
    @app_commands.describe(
        name="Name of the event (Select or type custom)",
        time="Time in UTC (MM-DD HH:MM or YYYY-MM-DD HH:MM)",
        repeat="Number of times to repeat (optional)",
        interval="Interval between repeats e.g. 2d, 1w, 12h (optional)"
    )
    @app_commands.autocomplete(name=name_autocomplete)
    async def add_event(self, interaction: discord.Interaction, name: str, time: str, repeat: int = 0, interval: str = None):
        # Defer response since DB ops might take a moment
        await interaction.response.defer()

        try:
            # Try parsing with year first
            start_time = datetime.datetime.strptime(time, "%Y-%m-%d %H:%M")
        except ValueError:
            try:
                # Try parsing without year (assume current year)
                dt_no_year = datetime.datetime.strptime(time, "%m-%d %H:%M")
                current_year = datetime.datetime.now().year
                start_time = dt_no_year.replace(year=current_year)
            except ValueError:
                await interaction.followup.send("Invalid time format. Please use `MM-DD HH:MM` or `YYYY-MM-DD HH:MM`", ephemeral=True)
                return

        interval_delta = self.parse_interval(interval)
        if repeat > 0 and not interval_delta:
            await interaction.followup.send("If you specify repeats, you must provide a valid interval (e.g., `1d`, `12h`).", ephemeral=True)
            return

        events_created = []
        current_time = start_time

        # Add the initial event
        await database.add_event(name, current_time, "") # Description removed as per request
        events_created.append(current_time)

        # Add repeats
        for _ in range(repeat):
            current_time += interval_delta
            await database.add_event(name, current_time, "")
            events_created.append(current_time)

        # Format response
        msg = f"✅ Created **{len(events_created)}** event(s) for **{name}** starting at `{start_time} UTC`."
        if repeat > 0:
            msg += f"\nRepeats: {repeat} times, Interval: {interval}"
            msg += f"\nLast event: `{events_created[-1]} UTC`"
        
        await interaction.followup.send(msg)

    @app_commands.command(name="list", description="List upcoming events")
    async def list_events(self, interaction: discord.Interaction):
        events = await database.get_all_events()
        if not events:
            await interaction.response.send_message("No upcoming events.", ephemeral=True)
            return

        embed = discord.Embed(title="📅 Upcoming Events", color=discord.Color.blue())
        
        # Limit to 25 fields (Discord limit)
        for event in events[:25]:
            # Convert string time to datetime
            try:
                dt = datetime.datetime.strptime(event['event_time'], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # Fallback
                dt = datetime.datetime.strptime(event['event_time'], "%Y-%m-%d %H:%M:00")
            
            # Create Discord timestamp (Unix timestamp)
            # Assuming stored time is UTC
            unix_ts = int(dt.replace(tzinfo=datetime.timezone.utc).timestamp())
            
            embed.add_field(
                name=f"{event['name']} (ID: {event['id']})",
                value=f"🕒 <t:{unix_ts}:F> (<t:{unix_ts}:R>)",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="delete", description="Delete an event by ID")
    @app_commands.describe(event_id="The ID of the event to delete")
    async def delete_event(self, interaction: discord.Interaction, event_id: int):
        await database.delete_event(event_id)
        await interaction.response.send_message(f"🗑️ Event with ID **{event_id}** deleted.")

async def setup(bot):
    await bot.add_cog(Events(bot))
