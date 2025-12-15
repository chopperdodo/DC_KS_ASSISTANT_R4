import aiosqlite
import asyncio

async def inspect():
    async with aiosqlite.connect("scheduler.db") as db:
        print("--- Table Info: events ---")
        async with db.execute("PRAGMA table_info(events)") as cursor:
            columns = await cursor.fetchall()
            for col in columns:
                print(col)

if __name__ == "__main__":
    asyncio.run(inspect())
