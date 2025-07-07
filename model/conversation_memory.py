import sqlite3
import spacy
from datetime import datetime
from sentence_transformers import SentenceTransformer
import numpy as np
from fuzzywuzzy import fuzz  #  For better matching

class ConversationMemory:
    def __init__(self, db_path="conversation_memory.db"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.create_table()

        #  Load NLP Models
        self.nlp = spacy.load("fr_core_news_sm")  # French model (use "en_core_web_sm" for English)
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")  # Semantic search model
        
        print(" SpaCy & Sentence Transformers loaded successfully!")

    def create_table(self):
        """Create a table to store conversations if it doesn't exist."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                username TEXT,
                message TEXT,
                timestamp TEXT
            )
        ''')
        self.conn.commit()

    def store_message(self, user_id, username, message):
        """Save a message into the database."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute('''
            INSERT INTO conversations (user_id, username, message, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, message, timestamp))
        self.conn.commit()

    def detect_keywords(self, text):
        """Extract important keywords from the user's query using NLP."""
        doc = self.nlp(text)
        keywords = [token.lemma_.lower() for token in doc if token.pos_ in ["NOUN", "PROPN"]]
        return keywords
    
    def retrieve_similar_conversations(self, user_id, query, top_n=5):
        """Find past messages most similar to the query using NLP embeddings and fuzzy matching."""
        self.cursor.execute("SELECT message, timestamp FROM conversations WHERE user_id = ?", (user_id,))
        messages = self.cursor.fetchall()

        if not messages:
            return []

        query_embedding = self.embedder.encode(query, convert_to_numpy=True)
        message_embeddings = [self.embedder.encode(msg, convert_to_numpy=True) for msg, _ in messages]

        # Compute cosine similarity
        similarities = [np.dot(query_embedding, emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(emb))
                        for emb in message_embeddings]

        #  Sort by similarity & fuzzy matching
        sorted_results = sorted(
            [(msg, timestamp, score) for (msg, timestamp), score in zip(messages, similarities)],
            key=lambda x: x[2], reverse=True
        )
        
        #  Apply fuzzy matching for better topic recognition
        final_results = [
            (msg, timestamp) for msg, timestamp, score in sorted_results
            if score > 0.5 or fuzz.ratio(query.lower(), msg.lower()) > 70  # Flexible matching
        ][:top_n]

        return final_results
