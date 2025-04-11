import sqlite3
from datetime import datetime
import spacy
from fuzzywuzzy import fuzz

class TaskModel:
    def __init__(self, reset_table=False):
        self.conn = sqlite3.connect('discord_tasks.db', check_same_thread=False)
        self.c = self.conn.cursor()
        if reset_table:
            self.drop_table_if_exists()
        self.create_table()
        self.create_checklist_table()
        self.nlp = spacy.load("fr_core_news_sm")  # ✅ Use French NLP model
        
    def drop_table_if_exists(self):
        """Drop the tasks table if it already exists."""
        self.c.execute("DROP TABLE IF EXISTS tasks")
        self.c.execute("DROP TABLE IF EXISTS checklists")
        self.conn.commit()
        print("✅ Dropped existing tables.")

    def get_tasks_by_keyword(self, keyword):
        """Retrieve tasks that contain related keywords using NLP & fuzzy matching."""
        self.c.execute("SELECT task_id, content, description, author, channel, status, timestamp FROM tasks")
        all_tasks = self.c.fetchall()

        # ✅ Extract the lemma (root word) of the keyword
        keyword_lemma = self.detect_keywords(keyword)

        matching_tasks = []
        for task in all_tasks:
            task_keywords = self.detect_keywords(task[1])  # ✅ Extract task name keywords

            # ✅ Fuzzy match with a threshold (allows similar words)
            if any(fuzz.ratio(kw, k) > 65 for kw in keyword_lemma for k in task_keywords):
                matching_tasks.append(task)

        return matching_tasks
    
    def detect_keywords(self, text):
        """Extract important keywords from the text using NLP."""
        doc = self.nlp(text)
        return [token.lemma_.lower() for token in doc if token.pos_ in ["NOUN", "PROPN"]]
    
    
    def get_tasks_by_author(self, author):
        """Retrieve all tasks for a specific author."""
        self.c.execute("SELECT task_id, content, description, author, channel, status, timestamp FROM tasks WHERE LOWER(author) = LOWER(?) ORDER BY timestamp DESC", (author,))
        return self.c.fetchall()

    def get_tasks_by_date(self, date):
        """Retrieve all tasks created on a specific date."""
        self.c.execute("SELECT task_id, content, description, author, channel, status, timestamp FROM tasks WHERE DATE(timestamp) = ? ORDER BY timestamp DESC", (date,))
        return self.c.fetchall()
    
    
    def get_tasks_by_relative_date(self, keyword):
        """Retrieve tasks based on relative date keywords: today, yesterday, tomorrow."""
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        if keyword.lower() == "today":
            return self.get_tasks_by_date(today)
        elif keyword.lower() == "yesterday":
            return self.get_tasks_by_date(yesterday)
        elif keyword.lower() == "tomorrow":
            return self.get_tasks_by_date(tomorrow)
        else:
            return []  # No valid date match

    def get_tasks_between_dates(self, from_date, till_date):
        """Retrieve tasks within a specific date range."""
        self.c.execute("SELECT task_id, content, description, author, channel, status, timestamp FROM tasks WHERE DATE(timestamp) BETWEEN ? AND ? ORDER BY timestamp DESC", (from_date, till_date))
        return self.c.fetchall()

    def get_tasks_by_status(self, status):
        """Retrieve all tasks with a specific status."""
        self.c.execute("SELECT task_id, content, description, author, channel, status, timestamp FROM tasks WHERE status = ? ORDER BY timestamp DESC", (status,))
        return self.c.fetchall()
    
    

    def get_tasks_for_today(self):
        """Retrieve all tasks submitted today."""
        today = datetime.now().strftime('%Y-%m-%d')
        self.c.execute("SELECT task_id, content, description, author, channel, status, timestamp FROM tasks WHERE DATE(timestamp) = ? ORDER BY timestamp DESC", (today,))
        return self.c.fetchall()


    def normalize_status(self,input_status):
        """Maps various user inputs to standardized status values."""
        status_mapping = {
            "in progress": "In Progress",
            "progress": "In Progress",
            "inprogress": "In Progress",
            "on hold": "On Hold",
            "onhold": "On Hold",
            "hold": "On Hold",
            "completed": "Completed",
            "complete": "Completed",
            "done": "Completed"
        }

        # Convert to lowercase & normalize spaces
        input_status = input_status.lower().strip()

        # Return normalized status or fallback to default
        return status_mapping.get(input_status, "In Progress")  # Default: "In Progress"


    def create_table(self):
        """Creates tasks table with correct schema."""
        self.c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            content TEXT,
                            description TEXT,
                            author TEXT,
                            channel TEXT,
                            status TEXT DEFAULT 'In Progress',
                            timestamp TEXT,
                            language TEXT
                        )''')
        self.conn.commit()

        # 🔥 Ensure columns match expected fields
        self.c.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in self.c.fetchall()]
        
        expected_columns = ["task_id", "content", "description", "author", "channel", "status", "timestamp", "language"]

        # 🔥 If the database has incorrect columns, reset it
        if set(columns) != set(expected_columns):
            print("⚠ Table schema mismatch detected! Resetting database...")
            self.drop_table_if_exists()
            self.create_table()


    def create_checklist_table(self):
        """Create checklist table for task-related items."""
        self.c.execute('''CREATE TABLE IF NOT EXISTS checklists (
                            checklist_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            task_id INTEGER,
                            content TEXT,
                            is_completed BOOLEAN DEFAULT 0,
                            timestamp TEXT,
                            author TEXT,
                            FOREIGN KEY (task_id) REFERENCES tasks (task_id) ON DELETE CASCADE
                        )''')
        self.conn.commit()


    def get_task_by_name(self, task_name):
        """Fetch a task by its name."""
        self.c.execute("SELECT task_id, content, description, author, channel, status, timestamp FROM tasks WHERE content = ?", (task_name,))
        return self.c.fetchone()  # Returns None if no task is found





    def store_task(self, content, description,author, channel, language='unknown'):
        """Store a new task in the database with default 'In Progress' status."""
        timestamp = str(datetime.now())
        try:
            self.c.execute("INSERT INTO tasks (content,description, author, channel, status, timestamp, language) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (content,description, author, channel, "In Progress", timestamp, language))
            self.conn.commit()
            print(f"✅ Stored task from {author} in {channel}: '{content}' with description '{description}' [Status: In Progress]")
        except sqlite3.Error as e:
            print(f"❌ Error inserting task: {e}")

    def update_task_status(self, task_id, new_status):
        """Update task status with normalized input."""
        normalized_status = self.normalize_status(new_status)
        self.c.execute("UPDATE tasks SET status = ? WHERE task_id = ?", (normalized_status, task_id))
        self.conn.commit()
        
    def update_task(self, task_id, new_name, new_description, new_status):
        """Updates the task name, description, and status in the database."""
        self.c.execute("UPDATE tasks SET content = ?, description = ?, status = ? WHERE task_id = ?", 
                    (new_name, new_description, new_status, task_id))
        self.conn.commit()



    def mark_task_complete(self, task_id):
        """Mark task as completed."""
        self.update_task_status(task_id, "Completed")

    def delete_task_by_id(self, task_id):
        """Delete a task by ID."""
        self.c.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
        self.conn.commit()

    def get_all_tasks(self):
        """Retrieve all tasks from the database in descending order to show newest first."""
        self.c.execute("SELECT task_id, content,description, author, channel, status, timestamp FROM tasks ORDER BY task_id DESC")
        return self.c.fetchall()

    def insert_classified_sentence(self, author, sentence, category, channel="classified", language="unknown"):
        timestamp = str(datetime.now())
        self.c.execute("""
            INSERT INTO tasks (content, description, author, channel, status, timestamp, language)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (sentence, f"[Category]: {category}", author, channel, "open", timestamp, language))
        self.conn.commit()


