import sqlite3
import discord


class DataService:
    def __init__(self, data_model):
        self.data_model = data_model
        self.conn = sqlite3.connect("messages.db")
        self.cursor = self.conn.cursor()

        # Ensure the table exists
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                author TEXT,
                content TEXT,
                is_report INTEGER
            )
        ''')
        self.conn.commit()

    async def fetch_and_store_messages(self, client, channel_name="reporting"):
        """Fetch messages from the channel and store them in the SQLite database."""
        channel = discord.utils.get(client.get_all_channels(), name=channel_name)
        if not channel:
            print(f"Channel '{channel_name}' not found.")
            return 0

        fetched_count = 0
        async for message in channel.history(limit=10000):
            if not self.message_exists(message.id):
                is_report = 1 if self.is_report(message.content) else 0
                self.cursor.execute('''
                    INSERT INTO messages (timestamp, author, content, is_report)
                    VALUES (?, ?, ?, ?)
                ''', (message.created_at.strftime('%Y-%m-%d %H:%M:%S'), str(message.author), message.content, is_report))
                fetched_count += 1

        self.conn.commit()
        print(f"Stored {fetched_count} new messages in SQLite.")
        return fetched_count

    def message_exists(self, message_id):
        """Check if the message with the given ID already exists in the database."""
        self.cursor.execute("SELECT 1 FROM messages WHERE id = ?", (message_id,))
        return self.cursor.fetchone() is not None

    def is_report(self, message_content):
        """Determine if a message is a report based on predefined keywords."""
        report_keywords = ["Rapport Quotidien d'Activité", "Projet", "Tâche", "Suivi", "Résumé"]
        return any(keyword.lower() in message_content.lower() for keyword in report_keywords)

    def save_classified_sentences(self, results):
        conn = sqlite3.connect("classified_sentences.db")
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categorized_sentences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sentence TEXT,
                category TEXT,
                timestamp TEXT
            )
        ''')

        for item in results:
            cursor.execute('''
                INSERT INTO categorized_sentences (sentence, category, timestamp)
                VALUES (?, ?, datetime('now'))
            ''', (item['sentence'], item['category']))

        conn.commit()
        conn.close()

    def get_daily_classification_summary(self):
        conn = sqlite3.connect("classified_sentences.db")
        cursor = conn.cursor()

        cursor.execute('''
            SELECT category, sentence FROM categorized_sentences
            WHERE date(timestamp) = date('now')
        ''')

        data = cursor.fetchall()
        conn.close()

        if not data:
            return "No categorized tasks found today."

        # Group by category
        summary = {}
        for category, sentence in data:
            summary.setdefault(category, []).append(sentence)

        # Format as a Discord message
        report = "** Daily Categorized Task Summary**\n"
        for cat, items in summary.items():
            report += f"\n**{cat.capitalize()}**:\n"
            for s in items:
                report += f"• {s}\n"

        return report
