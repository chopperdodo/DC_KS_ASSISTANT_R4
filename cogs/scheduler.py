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

    async def send_reminder_embed(self, channel, event, minutes_left, alert_type="Normal"):
        """Helper to send the Card-style reminder"""
        # Parse time
        try:
            dt = datetime.datetime.strptime(event['event_time'], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            dt = datetime.datetime.strptime(event['event_time'], "%Y-%m-%d %H:%M:%S.%f")
        
        unix_ts = int(dt.replace(tzinfo=datetime.timezone.utc).timestamp())
        
        # Defaults
        color = event['color_hex'] if event['color_hex'] else 0x3498db
        icon = event['icon_url'] if event['icon_url'] else "https://img.icons8.com/color/96/calendar--v1.png"
        e_type = event['event_type'] if event['event_type'] else "General"
        
        # Urgency override
        if minutes_left <= 15 and e_type == "Shield":
            title_prefix = "🚨 URGENT SHIELD ALERT / 護盾緊急提醒"
            color = 0xff0000
        elif minutes_left <= 5:
            title_prefix = "⚡ HURRY UP / 快點"
            color = 0xff0000
        else:
            title_prefix = f"🔔 Reminder / 提醒 ({int(minutes_left)}m)"

        embed = discord.Embed(
            title=f"{title_prefix}: {event['name']}",
            description=event['description'] or "No description",
            color=color
        )
        embed.set_thumbnail(url=icon)
        
        # Grid Layout
        embed.add_field(name="⏰ Time / 時間", value=f"<t:{unix_ts}:F>\n<t:{unix_ts}:R>", inline=True)
             
        # Ping
        content = "@everyone"
        
        await channel.send(content=content, embed=embed)


    @tasks.loop(minutes=1)
    async def check_reminders(self):
        await self.bot.wait_until_ready()
        
        print(f"\n🔍 [SCHEDULER] check at {datetime.datetime.now().strftime('%H:%M:%S')}")
        
        # We need to fetch all upcoming events to check logic, 
        # but get_upcoming_reminders is optimized for just 30m/5m reminders.
        # We might need to check if we can add a 'reminder_15_sent' column later for Shield,
        # but for now let's rely on calculating diffs.
        # Actually database.py logic filters for (reminder_30_sent = 0 OR reminder_5_sent = 0).
        # This will MISS the 15m check if we don't update that query or just check all events.
        # For efficiency, let's stick to the existing query but maybe modifying it or just processing what we have.
        # Wait, if I want a 15 min reminder, I need to know if it was sent.
        # Since I didn't add `reminder_15_sent` to DB, I might spam it if I'm not careful.
        # Let's just hook into the existing flow: 30m and 5m are standard.
        # If it's a Shield event, maybe I treat the "30m" slot as "15m"? 
        # Or I just add a special check for Shield events if they are in the returned list.
        # The query `event_time > ?` returns everything in future.
        # The AND clause `(reminder_30_sent = 0 OR reminder_5_sent = 0)` filters out completed ones.
        # This means if I have a Shield event in 15 mins, and I haven't sent the 30m reminder (because it was >30m before?),
        # wait. 
        # If I want to support 15m specifically for Shield without DB schema change:
        # I can use the `reminder_30_sent` flag as "first warning sent" flag.
        
        events = await database.get_upcoming_reminders()
        now = datetime.datetime.now()
        
        # Cleanup
        await database.delete_old_events()

        for event in events:
            guild_id = event['guild_id']
            if not guild_id: continue
                
            channel_id = await database.get_guild_channel(guild_id)
            if not channel_id: continue

            try:
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    channel = await self.bot.fetch_channel(channel_id)
            except Exception as e:
                print(f"❌ Error getting channel: {e}")
                continue

            try:
                # Parse naive datetime from DB
                dt_naive = datetime.datetime.strptime(event['event_time'], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    dt_naive = datetime.datetime.strptime(event['event_time'], "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                     dt_naive = datetime.datetime.strptime(event['event_time'], "%Y-%m-%d %H:%M") # fallback

            # Assume stored time IS UTC (per user intent), so make it aware
            event_time = dt_naive.replace(tzinfo=datetime.timezone.utc)
            
            # Compare with UTC now
            now = datetime.datetime.now(datetime.timezone.utc)
            
            time_diff = event_time - now
            minutes_diff = time_diff.total_seconds() / 60
            
            # Logic:
            # Shield Events: 15m ALERT (High Priority), then 5m
            # Normal Events: 30m Reminder, then 5m
            
            e_type = event['event_type']
            
            # 30 Minute Reminder (Normal)
            if e_type != "Shield" and 25 <= minutes_diff <= 35 and not event['reminder_30_sent']:
                print(f"  🔔 Sending 30m reminder for {event['name']}")
                await self.send_reminder_embed(channel, event, minutes_diff)
                await database.mark_reminder_sent(event['id'], "30")

            # 15 Minute Reminder (Shield Only)
            # We reuse the "30" flag or "5" flag? No, if we want a distinct one, we need a column.
            # Workaround: For Shield, if minutes_diff <= 15 and NOT reminder_30_sent (using 30 as 'early warning' slot)
            elif e_type == "Shield" and 10 <= minutes_diff <= 20 and not event['reminder_30_sent']:
                print(f"  🛡️ Sending 15m Shield Alert for {event['name']}")
                await self.send_reminder_embed(channel, event, minutes_diff)
                await database.mark_reminder_sent(event['id'], "30") # Mark "early warning" as done

            # 5 Minute Reminder (All)
            elif 0 < minutes_diff <= 5 and not event['reminder_5_sent']:
                print(f"  ⚡ Sending 5m reminder for {event['name']}")
                await self.send_reminder_embed(channel, event, minutes_diff)
                await database.mark_reminder_sent(event['id'], "5")

async def setup(bot):
    await bot.add_cog(Scheduler(bot))
