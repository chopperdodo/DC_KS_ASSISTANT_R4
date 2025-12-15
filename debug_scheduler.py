import asyncio
import aiosqlite
import datetime
import os

DB_NAME = "scheduler.db"

async def check():
    print(f"Current System Time (Local): {datetime.datetime.now()}")
    print(f"Current UTC Time: {datetime.datetime.now(datetime.timezone.utc)}")
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        
        # 1. Check get_upcoming_reminders logic
        now = datetime.datetime.now()
        print(f"\nScanning DB with naive cutoff: {now}")
        
        async with db.execute("SELECT * FROM events") as cursor:
            all_events = await cursor.fetchall()
            print(f"Total events in DB: {len(all_events)}")
            for e in all_events:
                 print(f" - [{e['id']}] {e['name']} at {e['event_time']} | 30Sent: {e['reminder_30_sent']} | 5Sent: {e['reminder_5_sent']}")

        async with db.execute(
            "SELECT * FROM events WHERE event_time > ? AND (reminder_30_sent = 0 OR reminder_5_sent = 0)",
            (now,)
        ) as cursor:
            upcoming = await cursor.fetchall()
            print(f"\nUpcoming events (Filtered by DB > {now}): {len(upcoming)}")
            
            for event in upcoming:
                # 2. Simulate Scheduler Logic
                try:
                    dt_naive = datetime.datetime.strptime(event['event_time'], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                         dt_naive = datetime.datetime.strptime(event['event_time'], "%Y-%m-%d %H:%M:%S.%f")
                    except:
                         dt_naive = datetime.datetime.strptime(event['event_time'], "%Y-%m-%d %H:%M")

                event_time = dt_naive.replace(tzinfo=datetime.timezone.utc)
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                
                time_diff = event_time - now_utc
                minutes_diff = time_diff.total_seconds() / 60
                
                print(f"   -> Event {event['id']} '{event['name']}':")
                print(f"      Stored: {event['event_time']} (Assumed UTC)")
                print(f"      Aware:  {event_time}")
                print(f"      NowUTC: {now_utc}")
                print(f"      Diff:   {minutes_diff:.2f} mins")
                
                # Logic Test
                is_shield = "Shield" in event['name']
                
                if not is_shield and 25 <= minutes_diff <= 35 and not event['reminder_30_sent']:
                    print("      [MATCH] 30m Reminder would fire")
                elif is_shield and 10 <= minutes_diff <= 20 and not event['reminder_30_sent']:
                    print("      [MATCH] 15m Shield Alert would fire")
                elif 0 < minutes_diff <= 5 and not event['reminder_5_sent']:
                    print("      [MATCH] 5m Reminder would fire")
                else:
                    print("      [NO MATCH] No condition met")

if __name__ == "__main__":
    try:
        asyncio.run(check())
    except KeyboardInterrupt:
        pass
