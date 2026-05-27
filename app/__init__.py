from flask import Flask
import os

def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config["SECRET_KEY"] = "horeca-ai-secret-2024"
    app.config["DATABASE"]   = os.path.join(os.path.dirname(os.path.dirname(__file__)), "instance", "horeca.db")

    from app.routes import main
    app.register_blueprint(main)

    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)
    from app.db import init_db
    with app.app_context():
        init_db()

    return app
