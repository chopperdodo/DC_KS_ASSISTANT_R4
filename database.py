import aiosqlite
import datetime
import os

DB_NAME = "kingshot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Enable foreign keys
        await db.execute("PRAGMA foreign_keys = ON")
        
        # Events table with guild_id
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                name TEXT NOT NULL,
                event_time TIMESTAMP NOT NULL,
                description TEXT,
                reminder_30_sent BOOLEAN DEFAULT 0,
                reminder_5_sent BOOLEAN DEFAULT 0
            )
        """)
        
        # Guild settings table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
        """)
        
        # Migration: Add guild_id column if it doesn't exist (for existing DBs)
        try:
            await db.execute("ALTER TABLE events ADD COLUMN guild_id INTEGER")
        except Exception:
            pass # Column likely exists
            
        await db.commit()

async def set_guild_channel(guild_id: int, channel_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO guild_settings (guild_id, channel_id) VALUES (?, ?)",
            (guild_id, channel_id)
        )
        await db.commit()

async def get_guild_channel(guild_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT channel_id FROM guild_settings WHERE guild_id = ?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def add_event(guild_id: int, name: str, event_time: datetime.datetime, description: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO events (guild_id, name, event_time, description) VALUES (?, ?, ?, ?)",
            (guild_id, name, event_time, description)
        )
        await db.commit()

async def get_all_events(guild_id: int = None):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        if guild_id:
            query = "SELECT * FROM events WHERE guild_id = ? ORDER BY event_time ASC"
            params = (guild_id,)
        else:
            query = "SELECT * FROM events ORDER BY event_time ASC"
            params = ()
            
        async with db.execute(query, params) as cursor:
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
        # Fetch all future events that haven't had both reminders sent
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
