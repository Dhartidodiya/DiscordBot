# services/task_classifier_service.py

import sqlite3

class TaskClassifierService:
    def __init__(self):
        self.conn = sqlite3.connect("classified_sentences.db")
        self.cursor = self.conn.cursor()

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS categorized_sentences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sentence TEXT,
                category TEXT,
                timestamp TEXT
            )
        ''')
        self.conn.commit()

    def save_classified_sentences(self, results):
        """Save NLP-classified task sentences to DB."""
        for item in results:
            self.cursor.execute('''
                INSERT INTO categorized_sentences (sentence, category, timestamp)
                VALUES (?, ?, datetime('now'))
            ''', (item['sentence'], item['category']))

        self.conn.commit()

    def get_daily_summary(self):
        """Fetch categorized sentences from today and group them."""
        self.cursor.execute('''
            SELECT category, sentence FROM categorized_sentences
            WHERE date(timestamp) = date('now')
        ''')

        rows = self.cursor.fetchall()
        if not rows:
            return "📌 No categorized tasks found today."

        summary = {}
        for category, sentence in rows:
            summary.setdefault(category, []).append(sentence)

        # Format for Discord
        report = "**📊 Daily Task Summary (by Category)**\n"
        for cat, items in summary.items():
            report += f"\n**{cat.capitalize()}**:\n"
            for s in items:
                report += f"• {s}\n"
        return report
