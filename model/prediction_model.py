import sqlite3
from datetime import datetime

class PredictionModel:
    def __init__(self):
        self.conn = sqlite3.connect('discord_tasks.db', check_same_thread=False)
        self.c = self.conn.cursor()
        self.ensure_table_exists()

    def ensure_table_exists(self):
        """Ensure the tasks table exists (shared with TaskModel)."""
        self.c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            content TEXT,
                            title TEXT,
                            description TEXT,
                            author TEXT,
                            channel TEXT,
                            status TEXT DEFAULT 'Completed',
                            label  TEXT,
                            emoji  TEXT,
                            timestamp TEXT,
                            language TEXT
                        )''')
        self.conn.commit()

    def store_prediction(self, sentence, title, author, channel_name, status, label ,
                         emoji, language="unknown"):
        """Store a classified task/prediction into the DB."""
        timestamp = str(datetime.now())
        description = title
        try:
            self.c.execute("""
                INSERT INTO tasks (content, description, author, channel, status, label, emoji, timestamp, language,title)
                VALUES (?, ?, ?, ?, ?, ?, ?,?,?,?)
            """, (sentence, description, author, channel_name, status, label, emoji, timestamp, language,title))
            self.conn.commit()
            print(f"✅ Stored prediction: {sentence} ({title}) in {channel_name}")
            print(f"✅ Stored: {sentence!r} | status={status}, label={label}, emoji={emoji}")
        except sqlite3.Error as e:
            print(f"❌ DB Error storing prediction: {e}")
