from flask import Blueprint,Flask, request, jsonify
from classify_model.classifier import classify_message 

# Create a Flask Blueprint
classify_api = Blueprint("classify_api", __name__)

# Route for classification
@classify_api.route("/api/predict", methods=["POST"])
def predict():
    data = request.get_json()
    message = data.get("message")

    if not message:
        return jsonify({"error": "Missing message"}), 400

    results = classify_message(message)
    return jsonify({"results": results})
