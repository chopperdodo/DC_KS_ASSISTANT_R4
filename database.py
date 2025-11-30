import aiosqlite
import datetime
import os

DB_NAME = "kingshot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                event_time TIMESTAMP NOT NULL,
                description TEXT,
                reminder_30_sent BOOLEAN DEFAULT 0,
                reminder_5_sent BOOLEAN DEFAULT 0
            )
        """)
        await db.commit()

async def add_event(name: str, event_time: datetime.datetime, description: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO events (name, event_time, description) VALUES (?, ?, ?)",
            (name, event_time, description)
        )
        await db.commit()

async def get_all_events():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM events ORDER BY event_time ASC") as cursor:
            return await cursor.fetchall()

async def delete_event(event_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM events WHERE id = ?", (event_id,))
        await db.commit()

async def get_upcoming_reminders():
    """
    Returns events that need reminders.
    """
    now = datetime.datetime.now()
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        # We need to fetch all future events and filter in python or do complex SQL
        # Simple approach: fetch all future events that haven't had both reminders sent
        async with db.execute(
            "SELECT * FROM events WHERE event_time > ? AND (reminder_30_sent = 0 OR reminder_5_sent = 0)",
            (now,)
        ) as cursor:
            return await cursor.fetchall()

async def mark_reminder_sent(event_id: int, reminder_type: str):
    async with aiosqlite.connect(DB_NAME) as db:
        if reminder_type == "30":
            await db.execute("UPDATE events SET reminder_30_sent = 1 WHERE id = ?", (event_id,))
        elif reminder_type == "5":
            await db.execute("UPDATE events SET reminder_5_sent = 1 WHERE id = ?", (event_id,))
        await db.commit()

async def delete_old_events():
    """Deletes events that are more than 24 hours past their start time."""
    cutoff = datetime.datetime.now() - datetime.timedelta(days=1)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM events WHERE event_time < ?", (cutoff,))
        await db.commit()
