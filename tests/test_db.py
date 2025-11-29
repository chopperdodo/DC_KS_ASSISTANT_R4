import asyncio
import datetime
import os
import sys

# Add parent directory to path to import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database

async def test_db():
    print("Initializing DB...")
    await database.init_db()
    
    print("Adding event...")
    now = datetime.datetime.now()
    future_30 = now + datetime.timedelta(minutes=30)
    future_5 = now + datetime.timedelta(minutes=5)
    
    await database.add_event("Test Event 30m", future_30, "Description 30m")
    await database.add_event("Test Event 5m", future_5, "Description 5m")
    
    print("Listing events...")
    events = await database.get_all_events()
    print(f"Found {len(events)} events.")
    for e in events:
        print(f"- {e['name']} at {e['event_time']}")
        
    print("Checking upcoming reminders...")
    reminders = await database.get_upcoming_reminders()
    print(f"Found {len(reminders)} reminders due.")
    
    if len(reminders) >= 2:
        print("SUCCESS: Reminders found.")
    else:
        print("FAILURE: Reminders not found.")

    print("Deleting events...")
    for e in events:
        await database.delete_event(e['id'])
    
    events_after = await database.get_all_events()
    if len(events_after) == 0:
        print("SUCCESS: Events deleted.")
    else:
        print("FAILURE: Events not deleted.")

if __name__ == "__main__":
    asyncio.run(test_db())
