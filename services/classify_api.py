from flask import Blueprint,Flask, request, jsonify
from classify_model.classifier import classify_message 
from model.task_model import TaskModel


# Create a Flask Blueprint
classify_api = Blueprint("classify_api", __name__)
task_model = TaskModel()


# Route for classification
@classify_api.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    message = data.get("message")
    

    if not message:
        return jsonify({"error": "Missing message"}), 400
    
    results = classify_message(message, include_title=True)
        
    return jsonify({"results": results})
