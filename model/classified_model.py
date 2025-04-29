import sqlite3
import pandas as pd
from datetime import datetime
import os

class ClassifiedModel:
    def __init__(self, db_path="classified_sentences.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        """Create the classified sentences table if it doesn't exist."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS classified_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                author TEXT,
                sentence TEXT,
                category TEXT,
                status TEXT DEFAULT 'open'
            )
        ''')
        self.conn.commit()

    def insert_classified_message(self, author, sentence, category, status="open"):
        """Insert a new classified sentence."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute('''
            INSERT INTO classified_messages (timestamp, author, sentence, category, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (timestamp, author, sentence, category, status))
        self.conn.commit()

    def import_from_csv(self, csv_path="classify_model/categorized_sentences.csv"):
        """Import data from CSV to database (one-time load)."""
        if not os.path.exists(csv_path):
            print("❌ CSV file not found.")
            return

        df = pd.read_csv(csv_path)

        # Optional: Check if already imported
        self.cursor.execute("SELECT COUNT(*) FROM classified_messages")
        existing_count = self.cursor.fetchone()[0]
        if existing_count > 0:
            print("⚠️ Data already exists in DB. Skipping import.")
            return

        # Make sure expected columns exist
        expected = {"Timestamp", "Author", "Sentence", "Category"}
        if not expected.issubset(df.columns):
            print("❌ CSV format is incorrect. Expected columns:", expected)
            return

        # Add default 'Status' if missing
        if "Status" not in df.columns:
            df["Status"] = "close"
        
        
        for _, row in df.iterrows():
            self.cursor.execute('''
                INSERT INTO classified_messages (timestamp, author, sentence, category, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (row["Timestamp"], row["Author"], row["Sentence"], row["Category"], row["Status"]))

        self.conn.commit()
        print(f"✅ Successfully imported {len(df)} rows from CSV into DB.")

    def get_all_messages(self):
        """Retrieve all classified messages."""
        self.cursor.execute("SELECT * FROM classified_messages ORDER BY id DESC")
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()
