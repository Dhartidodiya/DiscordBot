from flask import Flask
from services.api_service import api
from services.classify_api import classify_api
import os

def create_flask_server():
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY")

    # Register blueprints
    app.register_blueprint(api, url_prefix="/api")
    app.register_blueprint(classify_api, url_prefix="/api")

    return app
