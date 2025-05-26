from flask import Blueprint, jsonify, request
import sqlite3
from model.data_model import DataModel
from viewmodel.ml_viewmodel import MLViewModel
from datetime import datetime

api = Blueprint('api', __name__)

# Task DB - Read Only
@api.route('/api/tasks')
def get_tasks():
    conn = sqlite3.connect("discord_tasks.db")
    cursor = conn.cursor()
    cursor.execute("SELECT task_id, content, description, author, channel, status, timestamp, language FROM tasks")
    rows = cursor.fetchall()
    conn.close()

    tasks = []
    for r in rows:
        tasks.append({
            "task_id": r[0],
            "content": r[1],
            "description": r[2],
            "author": r[3],
            "channel": r[4],
            "status": r[5],
            "timestamp": r[6],
            "language": r[7]
        })
    return jsonify(tasks)



#  Train the model
@api.route('/api/train-model', methods=['POST'])
def train_model():
    data_model = DataModel()
    ml = MLViewModel(data_model)
    accuracy = ml.train_model()
    return jsonify({"accuracy": round(accuracy, 2)})


#  Conversation memory search
@api.route('/api/conversations')
def get_conversations():
    user_id = request.args.get('user_id')
    query = request.args.get('query')

    if not user_id or not query:
        return jsonify({"error": "Missing user_id or query"}), 400

    conn = sqlite3.connect("conversation_memory.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT message, timestamp FROM memory WHERE user_id = ? AND message LIKE ?",
        (user_id, f"%{query}%")
    )
    results = [{"message": r[0], "timestamp": r[1]} for r in cursor.fetchall()]
    conn.close()

    return jsonify(results)
