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
                reminder_5_sent BOOLEAN DEFAULT 0,
                event_type TEXT DEFAULT 'General',
                coordinates TEXT,
                repeat_config TEXT,
                icon_url TEXT,
                color_hex INTEGER
            )
        """)
        
        # Guild settings table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
        """)
        
        # Migration: Add columns if they don't exist (basic migration)
        try:
            await db.execute("ALTER TABLE events ADD COLUMN event_type TEXT DEFAULT 'General'")
            await db.execute("ALTER TABLE events ADD COLUMN coordinates TEXT")
            await db.execute("ALTER TABLE events ADD COLUMN repeat_config TEXT")
            await db.execute("ALTER TABLE events ADD COLUMN icon_url TEXT")
            await db.execute("ALTER TABLE events ADD COLUMN color_hex INTEGER")
        except Exception:
            pass # Columns likely exist or partial failure (SQLite simple migration)
            
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

async def add_event(guild_id: int, name: str, event_time: datetime.datetime, description: str, 
                    event_type: str = "General", coordinates: str = None, 
                    repeat_config: str = None, icon_url: str = None, color_hex: int = None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """INSERT INTO events 
               (guild_id, name, event_time, description, event_type, coordinates, repeat_config, icon_url, color_hex) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (guild_id, name, event_time, description, event_type, coordinates, repeat_config, icon_url, color_hex)
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
    """Deletes events that are more than 1 hour past their start time."""
    # Use naive UTC to match SQLite default string format
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM events WHERE event_time < ?", (cutoff,))
        await db.commit()
