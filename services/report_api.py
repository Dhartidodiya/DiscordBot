from flask import Blueprint, request, jsonify
from datetime import datetime
import sqlite3
from model.data_model import DataModel
from utils.date_parser import parse_date_range


report_api = Blueprint("report_api", __name__)
data_model = DataModel()

@report_api.route("/daily_report", methods=["GET"])
def daily_report():
    # Always use today's date
    today = datetime.now().date()
    start_date = end_date = today

    print(f" Daily report date: {start_date}")

    # Convert to datetime strings for SQL
    start_str = f"{start_date} 00:00:00"
    end_str = f"{end_date} 23:59:59"
    print(f" SQL range: {start_str} -> {end_str}")

    conn = sqlite3.connect("discord_tasks.db")
    cursor = conn.cursor()

    sql = """
    SELECT description as title, content, status, label,
           emoji, author, channel, timestamp
    FROM tasks
    WHERE timestamp BETWEEN ? AND ?
    ORDER BY title, timestamp
    """
    rows = cursor.execute(sql, (start_str, end_str)).fetchall()
    conn.close()

    return jsonify({"report": group_rows(rows)})



@report_api.route("/report_by_status", methods=["GET"])
def report_by_status():
    status = request.args.get("status", "").strip().lower()
    from_date_str = request.args.get("from")
    to_date_str = request.args.get("to")

    if not status:
        return jsonify({"report": []})

    try:
        if from_date_str and to_date_str:
            start_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()
        else:
            # default to wide range: Jan 1, 2000 to today
            start_date = datetime(2000, 1, 1).date()
            end_date = datetime.now().date()
    except ValueError:
        return jsonify({"report": []})

    start_str = f"{start_date} 00:00:00"
    end_str = f"{end_date} 23:59:59"

    conn = sqlite3.connect("discord_tasks.db")
    cursor = conn.cursor()
    sql = """
        SELECT description as title, content, status, label,
               emoji, author, channel, timestamp
        FROM tasks
        WHERE timestamp BETWEEN ? AND ? AND LOWER(status) = ?
        ORDER BY title, timestamp
    """
    rows = cursor.execute(sql, (start_str, end_str, status)).fetchall()
    conn.close()

    return jsonify({"report": group_rows(rows)})



@report_api.route("/report_by_user", methods=["GET"])
def report_by_user():
    user = request.args.get("user", "").strip().lower()
    user_id = request.args.get("user_id", "").strip()

    from_date_str = request.args.get("from")
    to_date_str = request.args.get("to")

    try:
        if from_date_str and to_date_str:
            start_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()
        else:
            start_date = datetime(2000, 1, 1).date()
            end_date = datetime.now().date()
    except ValueError:
        return jsonify({"report": []})

    start_str = f"{start_date} 00:00:00"
    end_str = f"{end_date} 23:59:59"

    conn = sqlite3.connect("discord_tasks.db")
    cursor = conn.cursor()

    try:
        if user_id:
            sql = """
                SELECT description as title, content, status, label,
                       emoji, author, channel, timestamp
                FROM tasks
                WHERE timestamp BETWEEN ? AND ? 
                  AND json_valid(author)
                  AND json_extract(author, '$.id') = ?
                ORDER BY title, timestamp
            """
            rows = cursor.execute(sql, (start_str, end_str, user_id)).fetchall()
        elif user:
            sql = """
                SELECT description as title, content, status, label,
                       emoji, author, channel, timestamp
                FROM tasks
                WHERE timestamp BETWEEN ? AND ?
                  AND json_valid(author)
                  AND LOWER(json_extract(author, '$.name')) = ?
                ORDER BY title, timestamp
            """
            rows = cursor.execute(sql, (start_str, end_str, user)).fetchall()
        else:
            return jsonify({"report": []})

    except sqlite3.OperationalError as e:
        # Fallback: try matching legacy plain-text author names
        print(f" SQLite JSON error: {e}. Falling back to plain author match.")
        if user:
            sql = """
                SELECT description as title, content, status, label,
                       emoji, author, channel, timestamp
                FROM tasks
                WHERE timestamp BETWEEN ? AND ?
                  AND LOWER(author) = ?
                ORDER BY title, timestamp
            """
            rows = cursor.execute(sql, (start_str, end_str, user)).fetchall()
        else:
            rows = []

    conn.close()
    return jsonify({"report": group_rows(rows)})





@report_api.route("/report_by_user_and_status", methods=["GET"])
def report_by_user_and_status():
    user = request.args.get("user", "").strip().lower()
    user_id = request.args.get("user_id", "").strip()
    status = request.args.get("status", "").strip().lower()

    if not status or (not user and not user_id):
        return jsonify({"report": []})

    from_date_str = request.args.get("from")
    to_date_str = request.args.get("to")

    try:
        if from_date_str and to_date_str:
            start_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()
        else:
            start_date = datetime(2000, 1, 1).date()
            end_date = datetime.now().date()
    except ValueError:
        return jsonify({"report": []})

    start_str = f"{start_date} 00:00:00"
    end_str = f"{end_date} 23:59:59"

    conn = sqlite3.connect("discord_tasks.db")
    cursor = conn.cursor()

    if user_id:
        sql = """
            SELECT description as title, content, status, label,
                   emoji, author, channel, timestamp
            FROM tasks
            WHERE timestamp BETWEEN ? AND ? 
              AND json_extract(author, '$.id') = ?
              AND LOWER(status) = ?
            ORDER BY title, timestamp
        """
        rows = cursor.execute(sql, (start_str, end_str, user_id, status)).fetchall()
    elif user:
        sql = """
            SELECT description as title, content, status, label,
                   emoji, author, channel, timestamp
            FROM tasks
            WHERE timestamp BETWEEN ? AND ? 
              AND LOWER(json_extract(author, '$.name')) = ?
              AND LOWER(status) = ?
            ORDER BY title, timestamp
        """
        rows = cursor.execute(sql, (start_str, end_str, user, status)).fetchall()
    else:
        return jsonify({"report": []})

    conn.close()
    return jsonify({"report": group_rows(rows)})



def group_rows(rows):
    grouped = {}
    for title, content, status, label, emoji, author, channel, timestamp in rows:
        if title not in grouped:
            grouped[title] = []
        grouped[title].append({
            "sentence": content,
            "status": status,
            "label": label,
            "emoji": emoji,
            "author": author,
            "channel": channel,
            "time": timestamp
        })
    return [{"title": title, "entries": entries} for title, entries in grouped.items()]