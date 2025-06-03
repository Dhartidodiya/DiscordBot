from flask import Flask

from services.classify_api import classify_api
from services.report_api import report_api
import os

def create_flask_server():
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY")

    # Register blueprints
    app.register_blueprint(classify_api, url_prefix="/api")
    app.register_blueprint(report_api, url_prefix="/api")

    return app
