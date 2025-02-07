from model.conversation_memory import ConversationMemory

class ConversationViewModel:
    def __init__(self):
        self.memory = ConversationMemory()

    def store_user_message(self, user_id, username, message):
        """Store a user message in the database."""
        self.memory.store_message(user_id, username, message)

    def get_past_messages(self, user_id, query):
        """Retrieve past messages related to the query."""
        keywords = self.memory.detect_keywords(query)
        if not keywords:
            return []
        
        best_keyword = keywords[0]  # Choose the most relevant keyword
        return self.memory.retrieve_similar_conversations(user_id, best_keyword, top_n=5)
