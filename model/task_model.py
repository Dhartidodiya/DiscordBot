# /model/task_model.py
import sqlite3
from datetime import datetime

class TaskModel:
    def __init__(self, reset_table=False):
        self.conn = sqlite3.connect('discord_tasks.db')
        self.c = self.conn.cursor()
        if reset_table:
            self.drop_table_if_exists()  # Call the method to drop the table if it exists (optional)
        self.create_table()
        self.create_checklist_table()  # Create the checklist table
        
    def drop_table_if_exists(self):
        """Drop the tasks table if it already exists."""
        self.c.execute("DROP TABLE IF EXISTS tasks")
        self.c.execute("DROP TABLE IF EXISTS checklists")
        self.conn.commit()
        print("Dropped the tasks table if it existed.")    

    def create_table(self):
        """Create the table to store tasks."""
        self.c.execute('''CREATE TABLE IF NOT EXISTS tasks
                          (task_id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, author TEXT, channel TEXT, timestamp TEXT, language TEXT)''')
        self.conn.commit()
        
        
    def create_checklist_table(self):
        """Create a checklist table for storing checklist items."""
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS checklists (
                checklist_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                content TEXT,
                is_completed BOOLEAN DEFAULT 0,
                timestamp TEXT,
                author TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks (task_id) ON DELETE CASCADE
            )
        ''')
        self.conn.commit()    

        
    def store_task(self,content, author, channel, language='unknown'):
        """Store the task into the database with an auto-incrementing task ID."""
        timestamp = str(datetime.now())  # Capture the current timestamp
        self.c.execute("INSERT OR IGNORE INTO tasks (content, author, channel, timestamp, language) VALUES (?, ?, ?, ?, ?)",
              (content, author, channel, timestamp, language))
        self.conn.commit()
        print(f"Stored task from {author} in {channel}: \n {content} [Language: {language}]")   



    def mark_task_complete(self, task_id):
        """Mark the task as completed."""
        self.c.execute("UPDATE tasks SET status = 'completed' WHERE task_id = ?", (task_id,))
        self.conn.commit()

    def delete_task(self, task_name):
        """Delete the task from the database."""
        self.c.execute("DELETE FROM tasks WHERE content = ?", (task_name,))
        self.conn.commit()

    def get_all_tasks(self):
        """Retrieve all tasks from the database."""
        self.c.execute("SELECT * FROM tasks WHERE status = 'active'")
        return self.c.fetchall()
    
    
    def delete_task(self, content):
        """Delete a task and its associated checklists by task content."""
        self.c.execute("DELETE FROM tasks WHERE content = ?", (content,))
        self.conn.commit()

    def get_all_tasks(self):
        """Retrieve all tasks from the database."""
        self.c.execute("SELECT * FROM tasks")
        return self.c.fetchall()
    
    def add_checklist_item(self, task_id, content, author):
        """Add a new checklist item linked to a task."""
        timestamp = str(datetime.now())
        self.c.execute("INSERT INTO checklists (task_id, content, author, timestamp) VALUES (?, ?, ?, ?)",
                       (task_id, content, author, timestamp))
        self.conn.commit()

    def get_checklists_by_task_id(self, task_id):
        """Get all checklist items for a specific task by its ID."""
        self.c.execute("SELECT checklist_id, content, is_completed FROM checklists WHERE task_id = ?", (task_id,))
        return self.c.fetchall()
    
    def toggle_checklist_status(self, checklist_id, task_id):
        """Toggle the completion status of a checklist item."""
        self.c.execute("SELECT is_completed FROM checklists WHERE checklist_id = ? AND task_id = ?", (checklist_id, task_id))
        status = self.c.fetchone()
        if status:
            new_status = not status[0]
            self.c.execute("UPDATE checklists SET is_completed = ? WHERE checklist_id = ?", (new_status, checklist_id))
            self.conn.commit()
    
    def get_tasks_by_date(self,query_date):
        """Retrieve all tasks for all users on a specific date."""
        self.c.execute("SELECT content, author, channel FROM tasks WHERE date(timestamp) = ?", (query_date,))
        tasks = self.c.fetchall()

        # Group tasks by author and channel
        grouped_tasks = {}
        for task in tasks:
            content, author, channel = task
            if author not in grouped_tasks:
                grouped_tasks[author] = {}
            if channel not in grouped_tasks[author]:
                grouped_tasks[author][channel] = []
            grouped_tasks[author][channel].append(content)

        return grouped_tasks  # Return tasks grouped by author and channel

    
    def get_tasks_by_author(self, author):
        """Retrieve all tasks for a specific user, sorted by date."""
        self.c.execute("SELECT content, channel, timestamp FROM tasks WHERE author = ? ORDER BY timestamp ASC", (author,))
        tasks = self.c.fetchall()

        grouped_tasks = {}
        for task in tasks:
            content, channel, timestamp = task
            # Format the timestamp to display in DD/MM/YYYY format
            formatted_date = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f').strftime('%d/%m/%Y')
            
            if channel not in grouped_tasks:
                grouped_tasks[channel] = []
            grouped_tasks[channel].append((content, formatted_date))

        return grouped_tasks
    
    def get_tasks_by_author_and_date(self, author, query_date):
        """Retrieve all tasks for a specific user on a specific date, including the date information."""
        self.c.execute("SELECT content, channel, date(timestamp) FROM tasks WHERE author = ? AND date(timestamp) = ?", (author, query_date))
        tasks = self.c.fetchall()

        grouped_tasks = {}
        for task in tasks:
            content, channel, date = task  # Include the date in the task retrieval
            
            # Format the date to DD/MM/YYYY format if needed
            formatted_date = datetime.strptime(date, '%Y-%m-%d').strftime('%d/%m/%Y')
            if channel not in grouped_tasks:
                grouped_tasks[channel] = []
            grouped_tasks[channel].append((content, formatted_date))  # Append content and date as a tuple

        return grouped_tasks


    def get_tasks_by_author_till_date(self, author, query_date):
        """Retrieve all tasks for a specific user up to a specified date."""
        print(f"Fetching tasks for author: {author} till date: {query_date}")  # Debug: Print function inputs
        
        self.c.execute("SELECT content, channel, date(timestamp) FROM tasks WHERE author = ? AND date(timestamp) <= ? ORDER BY timestamp ASC", 
                       (author, query_date))
        tasks = self.c.fetchall()
        print(f"Raw tasks fetched from database: {tasks}")  # Debug: Print raw fetched tasks

        grouped_tasks = {}
        for task in tasks:
            content, channel, date = task
            print(f"Processing task: Content='{content}', Channel='{channel}', Date='{date}'")  # Debug: Print each task detail

            # Format the date to DD/MM/YYYY format
            formatted_date = datetime.strptime(date, '%Y-%m-%d').strftime('%d/%m/%Y')

            if channel not in grouped_tasks:
                grouped_tasks[channel] = []
            grouped_tasks[channel].append((content, formatted_date))  # Append a tuple instead of two separate arguments
            
        print(f"Grouped tasks by channel: {grouped_tasks}") 
        return grouped_tasks
    
    def get_tasks_till_date(self, query_date):
        """Retrieve all tasks for all users till a specific date."""
        self.c.execute("SELECT content, author, channel FROM tasks WHERE date(timestamp) <= ?", (query_date,))
        tasks = self.c.fetchall()

        # Group tasks by author and channel
        grouped_tasks = {}
        for task in tasks:
            content, author, channel = task
            if author not in grouped_tasks:
                grouped_tasks[author] = {}
            if channel not in grouped_tasks[author]:
                grouped_tasks[author][channel] = []
            grouped_tasks[author][channel].append(content)

        return grouped_tasks  # Return tasks grouped by author and channel



