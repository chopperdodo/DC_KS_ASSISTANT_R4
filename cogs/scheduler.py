import discord
from discord.ext import commands, tasks
import datetime
import database
import os

class Scheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_reminders.start()
        print("✅ Scheduler initialized - reminder checking will start in 1 minute")

    def cog_unload(self):
        self.check_reminders.cancel()

    @tasks.loop(minutes=1)
    async def check_reminders(self):
        # Wait for bot to be ready
        await self.bot.wait_until_ready()
        
        print(f"\n🔍 [SCHEDULER] Running reminder check at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        events = await database.get_upcoming_reminders()
        now = datetime.datetime.now()
        
        print(f"📊 [SCHEDULER] Found {len(events)} upcoming events with pending reminders")

        if len(events) == 0:
            print("ℹ️ [SCHEDULER] No events need reminders at this time")

        # Auto-cleanup old events
        await database.delete_old_events()

        for event in events:
            # Get guild channel
            guild_id = event['guild_id']
            if not guild_id:
                # Legacy event or error
                print(f"⚠️ Event {event['id']} has no guild_id, skipping")
                continue
                
            channel_id = await database.get_guild_channel(guild_id)
            if not channel_id:
                print(f"⚠️ Guild {guild_id} has no channel set, skipping reminder for event {event['id']}")
                continue

            try:
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    # Try fetching if not in cache
                    channel = await self.bot.fetch_channel(channel_id)
            except Exception as e:
                print(f"❌ Could not get channel {channel_id}: {e}")
                continue

            # event_time is a string in ISO format (or whatever sqlite stores)
            # aiosqlite/sqlite3 default timestamp is usually string "YYYY-MM-DD HH:MM:SS"
            # We need to parse it back to datetime
            try:
                event_time = datetime.datetime.strptime(event['event_time'], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # Try without seconds if that fails, or handle other formats
                try:
                    event_time = datetime.datetime.strptime(event['event_time'], "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                     # Fallback for simple format
                    event_time = datetime.datetime.strptime(event['event_time'], "%Y-%m-%d %H:%M:00")

            time_diff = event_time - now
            minutes_diff = time_diff.total_seconds() / 60
            
            print(f"\n  📅 Event: {event['name']} (ID: {event['id']})")
            print(f"     Guild ID: {guild_id}")
            print(f"     Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"     Event time:   {event_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"     Time until event: {minutes_diff:.1f} minutes")

            # Create Discord timestamp
            unix_ts = int(event_time.replace(tzinfo=datetime.timezone.utc).timestamp())
            utc_str = event_time.strftime('%Y-%m-%d %H:%M')

            # 30 minute reminder (check if between 25 and 35 mins to be safe)
            if 25 <= minutes_diff <= 35 and not event['reminder_30_sent']:
                print(f"  🔔 [REMINDER] Sending 30-minute reminder for '{event['name']}'")
                
                await channel.send(
                    f"@everyone\n"
                    f"**{event['name']}** happens in 30 mins\n"
                    f"at time: {utc_str} UTC\n"
                    f"your local timezone: <t:{unix_ts}:F>"
                )
                await database.mark_reminder_sent(event['id'], "30")
                print(f"  ✅ [REMINDER] 30-minute reminder sent!")
            
            # 5 minute reminder
            elif 0 < minutes_diff <= 5 and not event['reminder_5_sent']:
                print(f"  🔔 [REMINDER] Sending 5-minute reminder for '{event['name']}'")
                
                await channel.send(
                    f"@everyone\n"
                    f"Hurry up\n"
                    f"**{event['name']}** happens in 5 mins\n"
                    f"at time: {utc_str} UTC\n"
                    f"your local timezone: <t:{unix_ts}:F>"
                )
                await database.mark_reminder_sent(event['id'], "5")
                print(f"  ✅ [REMINDER] 5-minute reminder sent!")
            else:
                print(f"  ⏸️ [REMINDER] No reminder needed at this time")

async def setup(bot):
    await bot.add_cog(Scheduler(bot))
