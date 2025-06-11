from flask import Blueprint, request, jsonify
from datetime import datetime
import sqlite3
from model.data_model import DataModel
from utils.date_parser import parse_date_range


report_api = Blueprint("report_api", __name__)
data_model = DataModel()

@report_api.route("/daily_report", methods=["GET"])
def daily_report():
    conn = sqlite3.connect("discord_tasks.db")
    cursor = conn.cursor()

    today = datetime.now().date()
    start = today.strftime('%Y-%m-%d 00:00:00')
    end = today.strftime('%Y-%m-%d 23:59:59')

    query = """
    SELECT description as title, content, status, label,
      emoji, author, channel, timestamp
    FROM tasks
    WHERE timestamp BETWEEN ? AND ?
    ORDER BY title, timestamp
    """
    rows = cursor.execute(query, (start, end)).fetchall()
    conn.close()

    grouped = {}

    for title, content, status, label, emoji, author, channel, timestamp in rows:
        if title not in grouped:
            grouped[title] = []

        grouped[title].append({
            "sentence": content,
            "status": status,
            "author": author,
            "channel": channel,
            "time": timestamp,
            "label":label,
            "emoji":emoji
        })

    # Convert to list of objects
    report = [
        {"title": title, "entries": entries}
        for title, entries in grouped.items()
    ]

    return jsonify({"report": report})