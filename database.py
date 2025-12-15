import aiosqlite
import datetime
import os
from constants import EventConfig

DB_NAME = "scheduler.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        
        # Events table with guild_id
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                name TEXT,
                event_time TIMESTAMP,
                description TEXT,
                reminder_30_sent INTEGER DEFAULT 0,
                reminder_5_sent INTEGER DEFAULT 0,
                event_type TEXT, -- 'Bear', 'Castle', etc.
                coordinates TEXT, -- '123,456'
                repeat_config TEXT, -- '1d', '7d', 'None'
                icon_url TEXT,
                color_hex INTEGER,
                duration INTEGER DEFAULT 0 -- Duration in minutes
            )
        """)
        
        # Guild settings table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                announcement_channel_id INTEGER
            )
        """)
        
        # MIGRATION: Add columns if they don't exist (SQLite doesn't support IF NOT EXISTS for columns easily)
        # We try to add them and ignore error if they exist.
        columns_to_add = [
            ("event_type", "TEXT"),
            ("coordinates", "TEXT"),
            ("repeat_config", "TEXT"),
            ("icon_url", "TEXT"),
            ("color_hex", "INTEGER"),
            ("duration", "INTEGER DEFAULT 0")
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                await db.execute(f"ALTER TABLE events ADD COLUMN {col_name} {col_type}")
                print(f"⚠️ Migrated DB: Added {col_name} column.")
            except Exception as e:
                # Column likely exists
                pass

        # DATA MIGRATION: Backfill duration for existing events
        # We iterate known event types and update duration where it is 0
        for name, data in EventConfig.EVENTS.items():
            duration = data.get("duration", 0)
            if duration > 0:
                # Update for main name
                await db.execute("UPDATE events SET duration = ? WHERE (name = ? OR event_type = ?) AND (duration IS NULL OR duration = 0)", (duration, name, name))
                # Update for legacy keys
                for key in data.get("legacy_keys", []):
                     await db.execute("UPDATE events SET duration = ? WHERE (name LIKE ? OR event_type = ?) AND (duration IS NULL OR duration = 0)", (duration, f"%{key}%", key))
            
        await db.commit()

async def set_guild_channel(guild_id: int, channel_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO guild_settings (guild_id, announcement_channel_id) VALUES (?, ?)",
            (guild_id, channel_id)
        )
        await db.commit()

async def get_guild_channel(guild_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT announcement_channel_id FROM guild_settings WHERE guild_id = ?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def add_event(guild_id, name, event_time, description, event_type, coordinates, repeat_config, icon_url, color_hex, duration=0):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO events (guild_id, name, event_time, description, event_type, coordinates, repeat_config, icon_url, color_hex, duration)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (guild_id, name, event_time, description, event_type, coordinates, repeat_config, icon_url, color_hex, duration))
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
