import asyncio
import aiosqlite
import datetime

async def inspect():
    async with aiosqlite.connect("scheduler.db") as db:
        db.row_factory = aiosqlite.Row
        print("--- Stored Events ---")
        async with db.execute("SELECT id, name, event_time FROM events") as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                print(f"ID: {row['id']} | Time: '{row['event_time']}'")
        
        print("\n--- Cutoff Check ---")
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        print(f"Cutoff (UTC - 1h): '{cutoff}'")
        
        # Test query
        print("\n--- Test Query ---")
        async with db.execute("SELECT id FROM events WHERE event_time < ?", (cutoff,)) as cursor:
            to_delete = await cursor.fetchall()
            print(f"Found {len(to_delete)} events to delete.")
            for row in to_delete:
                print(f" -> Would delete ID {row['id']}")

if __name__ == "__main__":
    asyncio.run(inspect())
