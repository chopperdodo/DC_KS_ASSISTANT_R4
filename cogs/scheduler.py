import discord
from discord.ext import commands, tasks
import datetime
import database
import os
from constants import EventConfig

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
        
        # Get metadata from Constants (consistent logic)
        # Note: Event name from DB is "Bear / 熊" hopefully. 
        # But if it's "Bear", get_event_metadata handles mapping.
        color, icon = EventConfig.get_event_metadata(event['name'])
        
        # Urgency override
        e_type = event['event_type']
        
        if minutes_left <= 15 and "Shield" in event['name']:
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
        
        try:
            print(f"\n🔍 [SCHEDULER] check at {datetime.datetime.now().strftime('%H:%M:%S')}")
            
            # Cleanup FIRST
            try:
                await database.delete_old_events()
            except Exception as e:
                print(f"❌ Error deleting old events: {e}")

            events = await database.get_upcoming_reminders()
            
            for event in events:
                try:
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
                    
                    # Use dictionary access (Fixed Bug)
                    e_type = event['event_type']
                    name = event['name']
                    
                    # 30 Minute Reminder (Normal)
                    is_shield = "Shield" in name
                    
                    # 30 Minute Reminder (Removed per user request)
                    # is_shield = "Shield" in name
                    # if not is_shield and 25 <= minutes_diff <= 35 and not event['reminder_30_sent']: ...

                    # 15 Minute Reminder (Shield Only)
                    if is_shield and 10 <= minutes_diff <= 20 and not event['reminder_30_sent']:
                        print(f"  🛡️ Sending 15m Shield Alert for {event['name']}")
                        await self.send_reminder_embed(channel, event, minutes_diff)
                        await database.mark_reminder_sent(event['id'], "30") # Reuse column for tracking

                    # 5 Minute Reminder (All)
                    elif 0 < minutes_diff <= 5 and not event['reminder_5_sent']:
                        print(f"  ⚡ Sending 5m reminder for {event['name']}")
                        await self.send_reminder_embed(channel, event, minutes_diff)
                        await database.mark_reminder_sent(event['id'], "5")
                        
                except Exception as e:
                    print(f"❌ Error processing event {event.get('id', '?')}: {e}")
                    import traceback
                    traceback.print_exc()

        except Exception as e:
            print(f"❌ Fatal Scheduler Error: {e}")
            import traceback
            traceback.print_exc()

async def setup(bot):
    await bot.add_cog(Scheduler(bot))
