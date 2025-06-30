import sqlite3
import discord
from discord.ext import commands
import json
class DataModel:
    def __init__(self, db_path="channel_data.db"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        """Create a table to store messages if it doesn't exist."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author TEXT,
                content TEXT,
                timestamp TEXT,
                channel_name TEXT
            )
        ''')
        self.conn.commit()

    async def fetch_data_from_neotech(self, client, channel_name="reporting"):
        """Fetch messages from the NeoTech channel by its name and store them in SQLite."""
        channel = discord.utils.get(client.get_all_channels(), name=channel_name)
        
        if channel is None:
            print(f"❌ Error: Channel '{channel_name}' not found.")
            return 0

        fetched_count = 0
        async for message in channel.history(limit=1000):
            if not message.author.bot:
                self.cursor.execute('''
                    INSERT INTO messages (author, content, timestamp, channel_name)
                    VALUES (?, ?, ?, ?)
                ''', (message.author.name, message.content, str(message.created_at), channel.name))
                fetched_count += 1
        self.conn.commit()
        # print(f"\n✅ Fetched and stored {fetched_count} messages from '{channel_name}' channel.")
        
        # # Print the fetched data
        # self.print_stored_data()
        
        return fetched_count

    def print_stored_data(self):
        """Query and print all the stored messages from the database."""
        self.cursor.execute("SELECT id, author, content, timestamp, channel_name FROM messages")
        rows = self.cursor.fetchall()
        
        if rows:
            print("\n📄 Stored Messages:")
            for row in rows:
                print(f"ID: {row[0]}, Author: {row[1]}, Content: {row[2]}, Timestamp: {row[3]}, Channel: {row[4]}")
        else:
            print("📭 No messages found in the database.")
