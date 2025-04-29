from flask import Flask, request, jsonify
from model.classified_model  import ClassifiedModel
import os

classified_model = ClassifiedModel()

# Import CSV just once at startup
classified_model.import_from_csv("classify_model/categorized_sentences.csv")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

@app.route("/api/classify", methods=["POST"])
def classify_and_store():
    data = request.json
    author = data.get("author")
    results = data.get("results")

    if not author or not results:
        return jsonify({"error": "Missing data"}), 400

    for item in results:
        classified_model.insert_classified_message(author, item["sentence"], item["category"])
        
    return jsonify({
        "message": "Stored successfully",
        "author": author,
        "entries_saved": len(results)
    }), 200    

 
# ✅ Health check endpoint (super useful for testing)
@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "OK"}), 200